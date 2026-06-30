"""Frío CLI (typer).

Phase 0 demoable surface:
  frio capabilities list                       # gated tools shown disabled + why
  frio competitors discover --seed "Spiritual Gangster"
  frio db init                                 # create tables (dev/test)
"""

from __future__ import annotations

import json

import typer

from .capabilities import REGISTRY, load_all_capabilities
from .config import load_config

app = typer.Typer(add_completion=False, help="Frío autonomous commerce agent")
capabilities_app = typer.Typer(help="Inspect capabilities")
competitors_app = typer.Typer(help="Competitor discovery (Phase 1a)")
research_app = typer.Typer(help="Ad research + strategist (Phase 1b)")
strategist_app = typer.Typer(help="Creative strategist (Phase 1b)")
product_app = typer.Typer(help="Product origin (Phase 2)")
creation_app = typer.Typer(help="AI-UGC video creation (Phase 3)")
optimize_app = typer.Typer(help="Optimize engine: kill/scale rules (Phase 4)")
analyzer_app = typer.Typer(help="Commercial/financial analyzer: product viability")
commerce_app = typer.Typer(help="Commerce / fulfillment (Phase 5, gated)")
ads_app = typer.Typer(help="Live ads + closed loop (Phase 6, most gated)")
db_app = typer.Typer(help="Database")
app.add_typer(capabilities_app, name="capabilities")
app.add_typer(competitors_app, name="competitors")
app.add_typer(research_app, name="research")
app.add_typer(strategist_app, name="strategist")
app.add_typer(product_app, name="product")
app.add_typer(creation_app, name="creation")
app.add_typer(optimize_app, name="optimize")
app.add_typer(analyzer_app, name="analyzer")
app.add_typer(commerce_app, name="commerce")
app.add_typer(ads_app, name="ads")
app.add_typer(db_app, name="db")


@capabilities_app.command("list")
def capabilities_list() -> None:
    """List all capabilities and whether they are enabled under current config."""
    load_all_capabilities()
    config = load_config()
    for cap in REGISTRY.all():
        on = cap.is_enabled(config)
        status = "ENABLED " if on else "disabled"
        line = f"  [{status}] {cap.name:24s} ({cap.category})  {cap.description}"
        typer.echo(line)
        if not on and cap.disabled_reason:
            typer.echo(f"             ↳ {cap.disabled_reason}")


@competitors_app.command("discover")
def competitors_discover(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    limit: int = typer.Option(20, help="Max competitors"),
) -> None:
    """Discover competitors who share our customers, ranked by similarity."""
    load_all_capabilities()
    config = load_config()
    seed = seed or config.seed_brands
    discover = REGISTRY.get("competitors.discover").func
    results = discover(seed=seed, limit=limit)
    typer.echo(f"Seed: {seed}")
    for c in results:
        typer.echo(
            f"  {c['similarity_score']:.2f}  {c['relation']:12s}  {c['name']}"
            + (f"  ({c['website']})" if c.get("website") else "")
        )
    typer.echo(json.dumps(results, indent=2))


@research_app.command("run")
def research_run(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    competitors: int = typer.Option(5, help="Max competitors to research"),
    ads: int = typer.Option(5, help="Ads per competitor"),
    persist: bool = typer.Option(True, help="Persist to the database"),
) -> None:
    """Discover competitors, pull their ads, and tear each down."""
    from .pipeline import run_phase1

    res = run_phase1(seed=seed, limit_competitors=competitors,
                     ads_per_competitor=ads, persist=persist)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys / LLM) — using deterministic fixtures.\n")
    typer.echo(f"Seed: {res.seed}")
    typer.echo(f"Competitors: {len(res.competitors)} | Ads torn down: {len(res.ads)}")
    if res.ads:
        t = res.ads[0]["teardown"]
        typer.echo(f"Sample teardown ({t.get('_engine')}): "
                   f"hook={t.get('hook')!r} angle={t.get('angle')!r}")
    if res.persisted:
        typer.echo(f"Persisted: {res.persisted}")


@strategist_app.command("plan")
def strategist_plan(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    out: str = typer.Option(None, help="Write the plan markdown to this path"),
    persist: bool = typer.Option(True, help="Persist research to the database"),
) -> None:
    """Produce the 30-day creative testing plan (the Phase 1 deliverable)."""
    from .modules.strategist import render_plan_markdown
    from .pipeline import run_phase1

    res = run_phase1(seed=seed, persist=persist)
    md = render_plan_markdown(res.plan)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys / LLM) — using deterministic fixtures.\n")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
        typer.echo(f"Wrote plan to {out}")
    else:
        typer.echo(md)


@product_app.command("discover")
def product_discover(
    niche: str = typer.Option(None, help="Niche (defaults to config niche)"),
    limit: int = typer.Option(20, help="Max products"),
    persist: bool = typer.Option(True, help="Persist to the database"),
) -> None:
    """Phase 2: pair your existing designs with competitor-recommended formats + mockup."""
    from .pipeline import run_phase2

    res = run_phase2(niche=niche, limit=limit, persist=persist)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys) — using deterministic fixtures.\n")
    typer.echo(f"Niche: {res.niche} | Pipeline: {res.pipeline}")
    if res.products:
        recs = res.products[0]["metadata"].get("recommended_blanks", [])
        typer.echo(f"Competitor-recommended formats: {', '.join(recs)}")
    typer.echo(f"Your designs to test: {len(res.products)}\n")
    for p in res.products:
        m, d = p["metadata"], p["metadata"]["demand"]
        typer.echo(f"  [{d['score']:.2f}] {p['title']}  →  on a {m['blank']}  "
                   f"(theme '{m['theme']}', vol={d['search_volume']})")
        typer.echo(f"          design={m['design_uri']}  mockup={m['mockup_uri']}")
    if res.persisted:
        typer.echo(f"\nPersisted: {res.persisted}")


@product_app.command("scale")
def product_scale(
    design_id: str = typer.Option(..., help="Winning design id (from `product discover`)"),
    niche: str = typer.Option(None, help="Niche (defaults to config)"),
    top: int = typer.Option(3, help="How many formats to scale onto"),
) -> None:
    """Phase 2: scale a winning design onto more competitor-recommended formats."""
    from .config import load_config
    from .modules.product_pod import scale_winner_to_formats

    cfg = load_config()
    cands = scale_winner_to_formats(design_id, niche or cfg.niche, cfg, top=top)
    if not cands:
        typer.echo(f"Design '{design_id}' not found in catalog.")
        raise typer.Exit(1)
    typer.echo(f"Scaling design '{design_id}' onto {len(cands)} formats:")
    for c in cands:
        m = c.metadata
        typer.echo(f"  • {m['blank']:12s} (fmt score {m['format_score']})  mockup={m['mockup_uri']}")


@creation_app.command("preview")
def creation_preview(
    niche: str = typer.Option(None, help="Niche (defaults to config)"),
    seed: str = typer.Option(None, help="Seed brand for hooks (defaults to config)"),
) -> None:
    """Build a UGC ad brief for the top product (spends nothing)."""
    from .pipeline import run_phase3

    res = run_phase3(niche=niche, seed=seed, approve=False)
    if not res.product:
        typer.echo(f"No product: {res.gate_message}")
        raise typer.Exit(1)
    typer.echo(f"Product: {res.product['title']}")
    typer.echo(f"Hook:    {res.brief['hook']}")
    typer.echo(f"Engine:  {res.brief['_engine']}")
    typer.echo(f"\nVideo prompt:\n  {res.brief['video_prompt']}")
    typer.echo(f"\nEstimated render cost: ${res.estimated_cost_usd:.2f} (no spend yet)")
    typer.echo("Run `frio creation render --approve` to render (gated + spend caps).")


@creation_app.command("render")
def creation_render(
    niche: str = typer.Option(None, help="Niche (defaults to config)"),
    seed: str = typer.Option(None, help="Seed brand for hooks (defaults to config)"),
    approve: bool = typer.Option(False, "--approve", help="Human approval to spend + render"),
) -> None:
    """Render the UGC MP4 (gated: needs creation enabled + approval + spend caps)."""
    from .pipeline import run_phase3

    res = run_phase3(niche=niche, seed=seed, approve=approve)
    if not approve:
        typer.echo("Dry run (no --approve): nothing rendered.")
        typer.echo(f"Would render '{res.brief['hook']}' for ~${res.estimated_cost_usd:.2f}.")
        return
    if res.rendered:
        r = res.rendered
        tag = " (offline placeholder, $0)" if r["offline"] else ""
        typer.echo(f"✅ Rendered: {r['uri']}  via {r['provider']}  "
                   f"cost=${r['cost_usd']:.2f}{tag}")
    else:
        typer.echo(f"⛔ Blocked by gate: {res.gate_message}")


@creation_app.command("carousel")
def creation_carousel(
    niche: str = typer.Option(None, help="Niche (defaults to config)"),
    seed: str = typer.Option(None, help="Seed brand for hooks (defaults to config)"),
    slides: int = typer.Option(4, help="Number of carousel slides"),
    approve: bool = typer.Option(False, "--approve", help="Human approval to spend + render"),
) -> None:
    """Build (and optionally render) a UGC image carousel (gated + spend caps)."""
    from .pipeline import run_phase3_carousel

    res = run_phase3_carousel(niche=niche, seed=seed, slides=slides, approve=approve)
    if not res.product:
        typer.echo(f"No product: {res.gate_message}")
        raise typer.Exit(1)
    typer.echo(f"Product: {res.product['title']}  | slides: {len(res.brief['slides'])}")
    for sl in res.brief["slides"]:
        typer.echo(f"  • {sl['caption']}")
    typer.echo(f"\nEstimated cost: ${res.estimated_cost_usd:.2f}")
    if not approve:
        typer.echo("Dry run (no --approve): nothing rendered. Add --approve to render.")
        return
    if res.rendered:
        r = res.rendered
        tag = " (offline placeholders, $0)" if r["offline"] else ""
        typer.echo(f"\n✅ Rendered {len(r['slides'])} slides, "
                   f"total=${r['total_cost_usd']:.2f}{tag}")
        for sl in r["slides"]:
            typer.echo(f"  slide {sl['slide']}: {sl['uri']}")
    else:
        typer.echo(f"\n⛔ Blocked by gate: {res.gate_message}")


@optimize_app.command("run")
def optimize_run(
    demo: bool = typer.Option(False, "--demo", help="Seed synthetic metrics first"),
    persist: bool = typer.Option(True, help="Record proposals to the decisions log"),
) -> None:
    """Evaluate ad metrics -> kill/scale/hold proposals (kills auto, scales need OK)."""
    from .pipeline import run_phase4

    res = run_phase4(seed_demo=demo, persist=persist)
    if not res.proposals:
        typer.echo("No metrics found. Try `frio optimize run --demo` to see it work.")
        return
    icon = {"kill": "🔪", "scale": "📈", "hold": "⏸️"}
    for p in res.proposals:
        gate = "" if p["action"] != "scale" else "  [NEEDS APPROVAL]"
        auto = "  [auto]" if p["auto_executable"] else ""
        typer.echo(f"  {icon.get(p['action'],'')} {p['action'].upper():5s} "
                   f"{p['entity_id']:12s} {p['reason']}{auto}{gate}")
    typer.echo(f"\nKills: {res.kills} (auto-applied: {res.auto_applied})  "
               f"Scales: {res.scales} (awaiting approval: {res.awaiting_approval})  "
               f"Holds: {res.holds}")
    typer.echo("Kills reduce spend (safe to auto-run); scale-ups raise spend (need sign-off).")


@analyzer_app.command("product")
def analyzer_product(
    price: float = typer.Option(..., help="Selling price per unit (USD)"),
    cost: float = typer.Option(..., help="Product cost per unit: base+print (USD)"),
    units: int = typer.Option(..., help="Units sold in the period"),
    ad_spend: float = typer.Option(..., help="Ad spend in the period (USD)"),
    fulfillment: float = typer.Option(0.0, help="Fulfillment cost per unit (USD)"),
    revenue: float = typer.Option(None, help="Override revenue (else price*units)"),
) -> None:
    """Compute a product's true P&L + a continue/scale/cancel verdict."""
    from .config import load_config
    from .modules.analyzer import analyze, cost_structure_from

    cfg = load_config()
    cs = cost_structure_from(cfg, price=price, product_cost=cost, fulfillment_cost=fulfillment)
    v = analyze(cs, units, ad_spend, cfg, revenue=revenue)
    p = v.pnl
    icon = {"cancel": "🛑", "watch": "⏸️", "continue": "✅", "scale": "🚀"}
    typer.echo(f"{icon.get(v.decision, '')} {v.decision.upper()} — {v.headline}\n")
    typer.echo(f"  Revenue ${p['revenue']:.2f} | Ad spend ${p['ad_spend']:.2f} | "
               f"Net profit ${p['net_profit']:.2f} ({p['net_margin']*100:.0f}% margin)")
    poas = p['poas']
    typer.echo(f"  Contribution/unit ${p['contribution_per_unit']:.2f} | "
               f"POAS {poas if poas is None else f'{poas:.2f}x'} | "
               f"break-even ROAS {p['break_even_roas']}")
    for r in v.reasons:
        typer.echo(f"    • {r}")


@commerce_app.command("publish")
def commerce_publish(
    niche: str = typer.Option(None, help="Niche (defaults to config)"),
    approve: bool = typer.Option(False, "--approve", help="Human approval to publish"),
) -> None:
    """Publish the top demand-validated product to the store (gated + HITL)."""
    from .pipeline import run_phase5_publish

    res = run_phase5_publish(niche=niche, approve=approve)
    if not res.product:
        typer.echo(f"No product: {res.gate_message}")
        raise typer.Exit(1)
    typer.echo(f"Product: {res.product['title']}  | pipeline: {res.product['kind']}")
    if res.listing_id:
        typer.echo(f"✅ Published: listing={res.listing_id} via {res.provider}")
    else:
        typer.echo(f"⛔ Blocked by gate: {res.gate_message}")
        typer.echo("   (Commerce stays disabled until your seller account is approved "
                   "and you approve each publish.)")


@ads_app.command("launch")
def ads_launch(
    name: str = typer.Option("frio-test", help="Campaign name"),
    budget: float = typer.Option(5.0, help="Daily budget (USD)"),
    approve: bool = typer.Option(False, "--approve", help="Human approval to spend"),
) -> None:
    """Launch a live TikTok campaign (gated: needs ads enabled + approval + caps)."""
    from .pipeline import run_phase6_launch

    res = run_phase6_launch(name, budget, approve=approve)
    if res.campaign_id:
        typer.echo(f"✅ Launched: {res.campaign_id}  ${res.daily_budget_usd:.2f}/day")
    else:
        typer.echo(f"⛔ Blocked by gate: {res.gate_message}")


@ads_app.command("loop")
def ads_loop(
    demo: bool = typer.Option(False, "--demo", help="Seed synthetic metrics first"),
) -> None:
    """Run the closed loop: auto-kill losers, surface winners for your approval."""
    from .pipeline import run_phase6_loop

    res = run_phase6_loop(seed_demo=demo)
    typer.echo(f"🔪 Kills auto-applied: {res['applied_kills']}")
    typer.echo(f"📈 Scale candidates awaiting your approval: {res['awaiting_approval']}")
    for p in res["pending_scales"]:
        typer.echo(f"   • {p['entity_id']}: {p['reason']}")
    typer.echo("\nKills run automatically (cut spend); scale-ups never auto-run "
               "(they raise spend — your call).")


@app.command("dashboard")
def dashboard_cmd(
    host: str = typer.Option("127.0.0.1", help="Bind address (default: local only)"),
    port: int = typer.Option(8787, help="Port"),
) -> None:
    """Launch the local, read-only, password-protected dashboard."""
    from .config import load_config

    cfg = load_config()
    if not cfg.dashboard_password:
        typer.echo("⛔ Set a password first:  export FRIO_DASHBOARD_PASSWORD='your-secret'")
        raise typer.Exit(1)
    try:
        import uvicorn

        from .dashboard import create_app
    except ImportError:
        typer.echo("Install the dashboard extra:  pip install -e '.[dashboard]'")
        raise typer.Exit(1)
    typer.echo(f"🧊 Frío dashboard → http://{host}:{port}  (user: {cfg.dashboard_user})")
    if host not in ("127.0.0.1", "localhost"):
        typer.echo("⚠ Binding beyond localhost exposes business data — use HTTPS + a strong password.")
    uvicorn.run(create_app(cfg), host=host, port=port, log_level="warning")


@app.command("compliance")
def compliance_check(text: str = typer.Argument(..., help="Ad creative text to scan")) -> None:
    """Scan ad creative for TikTok-prohibited claims (advisory)."""
    from .compliance import review_creative
    from .config import load_config

    rep = review_creative(text, requires_ai_disclosure=load_config().require_ai_disclosure)
    if rep["ok"]:
        typer.echo("✅ No prohibited-claim patterns found.")
    for v in rep["violations"]:
        typer.echo(f"⚠️  [{v['severity']}] {v['category']}: '{v['matched']}' — {v['note']}")
    if rep["needs_ai_disclosure"]:
        typer.echo("⚠️  Missing AI-UGC disclosure.")


@db_app.command("init")
def db_init() -> None:
    """Create all tables (dev/test convenience; Alembic owns prod migrations)."""
    from .db.base import init_db

    config = load_config()
    init_db(config.database_url)
    typer.echo(f"Initialized schema at {config.database_url}")


if __name__ == "__main__":
    app()
