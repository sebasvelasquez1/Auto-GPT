"""Static dashboard export (Netlify) — no web server / no fastapi needed."""

from __future__ import annotations

from frio.config import Config
from frio.dashboard_render import export_site, render_html
from frio.db.base import init_db, make_session_factory
from frio.db.models import Decision, Product, SpendLedger


def _seed(url: str) -> None:
    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        s.add(Product(kind="pod", title="Stay Grounded", source="existing-catalog",
                      demand_validated=True,
                      metadata_={"blank": "tank top", "demand": {"score": 0.42}}))
        s.add(SpendLedger(category="ads", amount_usd=25.0, reference="launch:test"))
        s.add(Decision(kind="kill", actor="engine", target="creative_A",
                       rationale="$25 spent, 0 ATC"))
        s.commit()


def test_render_html_contains_data(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'r.db'}"
    _seed(url)
    page = render_html(Config(database_url=url))
    assert "<!doctype html>" in page.lower()
    for needle in ["Stay Grounded", "tank top", "$25.00"]:
        assert needle in page


def test_export_site_writes_index_html(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'e.db'}"
    _seed(url)
    out = tmp_path / "site"
    path = export_site(Config(database_url=url), str(out))
    assert path.endswith("index.html")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "Stay Grounded" in html
