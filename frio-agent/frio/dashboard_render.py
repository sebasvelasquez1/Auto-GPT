"""Render the dashboard to HTML (no web server / no FastAPI needed).

Used by both the live FastAPI app (frio/dashboard.py) and the STATIC export that
Netlify (or any static host) publishes from GitHub. Read-only: it only renders the
calculations already in the database.
"""

from __future__ import annotations

import html
import os

from .config import Config
from .db.base import make_session_factory
from .db.models import Competitor, Decision, Product, SpendLedger


def _esc(x) -> str:
    return html.escape(str(x))


def _table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return "<p class=muted>— sin datos todavía —</p>"
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _card(label: str, value) -> str:
    return f"<div class=card><div class=num>{_esc(value)}</div><div class=lbl>{_esc(label)}</div></div>"


_CSS = """
body{font-family:system-ui,Arial,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
header{background:#161a22;padding:16px 24px;border-bottom:1px solid #262b36}
h1{font-size:18px;margin:0}h2{font-size:15px;color:#9aa4b2;margin:28px 24px 8px}
h2.headline{color:#e6e6e6;font-size:19px;margin:24px 24px 12px}
.cards{display:flex;gap:12px;flex-wrap:wrap;padding:16px 24px}
.card{background:#161a22;border:1px solid #262b36;border-radius:10px;padding:14px 18px;min-width:120px}
.num{font-size:22px;font-weight:700}.lbl{font-size:12px;color:#9aa4b2;margin-top:2px}
table{width:calc(100% - 48px);margin:0 24px;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #20242e}
th{color:#9aa4b2;font-weight:600}.muted{color:#6b7280;margin:0 24px}
footer{color:#6b7280;font-size:12px;padding:24px}
.verdicts{display:flex;flex-direction:column;gap:10px;padding:0 24px 8px}
.vcard{display:flex;align-items:center;gap:16px;border-radius:12px;padding:16px 20px;
border:1px solid #262b36}
.vcard.cancel{background:#2a1418;border-color:#5c2530}
.vcard.watch{background:#1c1f26;border-color:#2a2f3a}
.vcard.continue{background:#142a1a;border-color:#235c34}
.vcard.scale{background:#0f2b3a;border-color:#1f6f93}
.vcard.harvest{background:#2a2410;border-color:#6f5a1f}
.vbadge{font-size:13px;font-weight:700;padding:6px 12px;border-radius:8px;white-space:nowrap}
.vcard.cancel .vbadge{background:#5c2530;color:#ff9aa8}
.vcard.watch .vbadge{background:#2a2f3a;color:#9aa4b2}
.vcard.continue .vbadge{background:#235c34;color:#9af2b4}
.vcard.scale .vbadge{background:#1f6f93;color:#9adcff}
.vcard.harvest .vbadge{background:#6f5a1f;color:#f2dd9a}
.vtitle{font-weight:700;font-size:15px}.vsub{color:#9aa4b2;font-size:12px;margin-top:2px}
.vnums{margin-left:auto;text-align:right;font-size:13px;color:#cfd4dc}
.vnums b{font-size:15px;color:#fff}
"""


def _page(body: str) -> str:
    return (f"<!doctype html><html><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Frío</title><style>{_CSS}</style></head><body>"
            f"<header><h1>🧊 Frío — panel (solo lectura)</h1></header>{body}"
            f"<footer>Solo lectura. Las acciones que gastan dinero siguen con sus topes "
            f"y tu aprobación — no se ejecutan desde aquí.</footer></body></html>")


_VERDICT_LABEL = {"cancel": "🛑 NO SIRVE — cancelar", "watch": "⏸️ EN PRUEBA",
                  "continue": "✅ SIRVE — continuar", "scale": "🚀 SIRVE — escalar",
                  "harvest": "🌾 SIRVE — cosechar (no escalar más)"}


def _verdict_cards(config: Config) -> str:
    from .modules.analyzer import all_product_verdicts

    rows = all_product_verdicts(config)
    if not rows:
        return ("<p class=muted>Sin veredictos todavía — pon precio/costo a un producto "
               "con <code>frio product set-price</code> (o corre <code>frio demo-seed</code> "
               "para ver un ejemplo funcionando).</p>")
    cards = []
    for r in rows:
        v, p = r.viability, r.viability.pnl
        poas_txt = f"{p['poas']:.2f}x" if p["poas"] is not None else "—"
        cards.append(
            f"<div class='vcard {v.decision}'>"
            f"<div class=vbadge>{_VERDICT_LABEL.get(v.decision, v.decision)}</div>"
            f"<div><div class=vtitle>{_esc(r.title)} — {_esc(r.blank or r.kind)}</div>"
            f"<div class=vsub>{_esc(v.headline)}</div></div>"
            f"<div class=vnums><b>${p['net_profit']:.2f}</b> ganancia neta<br>"
            f"POAS {poas_txt} · {p['units']} ventas · ${p['ad_spend']:.0f} en ads</div></div>")
    return "<div class=verdicts>" + "".join(cards) + "</div>"


def render_html(config: Config) -> str:
    """Build the full dashboard page from the current database."""
    from .modules.optimize import propose_all

    verdicts_section = (
        "<h2 class=headline>📊 Resultados — ¿Sirve o no sirve cada diseño?</h2>"
        + _verdict_cards(config))

    Session = make_session_factory(config.database_url)
    with Session() as s:
        n_products = s.query(Product).count()
        n_competitors = s.query(Competitor).count()
        n_decisions = s.query(Decision).count()
        total_spend = sum(x.amount_usd for x in s.query(SpendLedger).all())

        products = [[p.title, p.kind, (p.metadata_ or {}).get("blank", "—"),
                     round((p.metadata_ or {}).get("demand", {}).get("score", 0), 2),
                     "✓" if p.demand_validated else ""]
                    for p in s.query(Product).limit(50).all()]

        verdicts = [[{"kill": "🔪", "scale": "📈", "hold": "⏸️"}.get(p.action, "")
                     + " " + p.action, p.entity_id, p.reason]
                    for p in propose_all(s, config, "creative")]

        decisions = [[d.created_at.strftime("%Y-%m-%d %H:%M"), d.kind, d.actor,
                      d.target or "—", d.rationale or ""]
                     for d in s.query(Decision).order_by(Decision.id.desc()).limit(20).all()]

        spend = [[x.created_at.strftime("%Y-%m-%d %H:%M"), x.category,
                  f"${x.amount_usd:.2f}", x.reference or ""]
                 for x in s.query(SpendLedger).order_by(SpendLedger.id.desc()).limit(20).all()]

    body = (
        verdicts_section
        + "<div class=cards>"
        + _card("Productos", n_products) + _card("Competidores", n_competitors)
        + _card("Decisiones", n_decisions) + _card("Gasto total", f"${total_spend:.2f}")
        + "</div>"
        + "<h2>Detalle técnico — productos (tus diseños × formato)</h2>"
        + _table(["Diseño", "Tipo", "Formato", "Demanda", "Validado"], products)
        + "<h2>Veredictos del optimizador (nivel anuncio)</h2>"
        + _table(["Acción", "Creativo", "Razón"], verdicts)
        + "<h2>Bitácora de decisiones (auditoría)</h2>"
        + _table(["Fecha", "Tipo", "Actor", "Objetivo", "Motivo"], decisions)
        + "<h2>Gasto (ledger)</h2>"
        + _table(["Fecha", "Categoría", "Monto", "Ref"], spend)
    )
    return _page(body)


def export_site(config: Config, out_dir: str = "site") -> str:
    """Write a static index.html snapshot (for Netlify / any static host)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(config))
    return path
