"""Dashboard tests — private, session-login protected. Skipped if fastapi absent."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("itsdangerous")  # required by starlette SessionMiddleware

from fastapi.testclient import TestClient  # noqa: E402

from frio.config import Config  # noqa: E402
from frio.dashboard import create_app  # noqa: E402
from frio.db.base import init_db, make_session_factory  # noqa: E402
from frio.db.models import Decision, MetricsDaily, Product, SpendLedger  # noqa: E402


def _client(tmp_path):
    url = f"sqlite:///{tmp_path/'dash.db'}"
    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        s.add(Product(kind="pod", title="369 Manifestation", source="existing-catalog",
                      demand_validated=True, metadata_={"blank": "tank top",
                                                        "demand": {"score": 0.42}}))
        winner = Product(kind="pod", title="Stay Grounded", source="existing-catalog",
                         price=30.0, unit_cost=9.0, fulfillment_unit_cost=5.0,
                         metadata_={"blank": "tank top"})
        s.add(winner)
        s.add(SpendLedger(category="ads", amount_usd=25.0, reference="launch:test"))
        s.add(Decision(kind="kill", actor="engine", target="creative_A",
                       rationale="$25 spent, 0 ATC"))
        s.commit()
        s.add(MetricsDaily(entity_type="product", entity_id=str(winner.id),
                           purchases=40, revenue_usd=1200.0, spend_usd=120.0))
        s.commit()
    cfg = Config(database_url=url, dashboard_password="secret123",
                 dashboard_session_secret="test-secret", dashboard_secure_cookies=False)
    # don't auto-follow redirects so we can assert the auth gate
    return TestClient(create_app(cfg), follow_redirects=False)


def test_unauthenticated_is_redirected_to_login(tmp_path) -> None:
    c = _client(tmp_path)
    r = c.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_wrong_password_is_rejected(tmp_path) -> None:
    c = _client(tmp_path)
    assert c.post("/login", data={"password": "nope"}).status_code == 401


def test_login_then_view_data(tmp_path) -> None:
    c = _client(tmp_path)
    r = c.post("/login", data={"password": "secret123"})
    assert r.status_code == 303 and r.headers["location"] == "/"
    page = c.get("/")  # session cookie now set
    assert page.status_code == 200
    for needle in ["369 Manifestation", "tank top", "$25.00", "Cerrar sesión",
                   "¿Sirve o no sirve", "SIRVE — escalar", "Stay Grounded",
                   "$424.00", "POAS 4.53x"]:
        assert needle in page.text
    # the business verdict appears BEFORE the raw technical tables
    assert page.text.index("¿Sirve o no sirve") < page.text.index("Detalle técnico")


def test_logout_clears_session(tmp_path) -> None:
    c = _client(tmp_path)
    c.post("/login", data={"password": "secret123"})
    c.get("/logout")
    assert c.get("/").status_code == 303  # back to login gate


def test_healthz_open(tmp_path) -> None:
    assert _client(tmp_path).get("/healthz").status_code == 200


def test_no_data_write_endpoints(tmp_path) -> None:
    # Only /login accepts POST (auth); nothing writes business data.
    app = _client(tmp_path).app
    posts = {r.path for r in app.routes if "POST" in getattr(r, "methods", set())}
    assert posts <= {"/login"}
