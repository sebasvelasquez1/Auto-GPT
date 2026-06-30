"""Dashboard tests — read-only + password-protected. Skipped if fastapi absent."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from frio.config import Config  # noqa: E402
from frio.dashboard import create_app  # noqa: E402
from frio.db.base import init_db, make_session_factory  # noqa: E402
from frio.db.models import Decision, Product, SpendLedger  # noqa: E402


def _client(tmp_path):
    url = f"sqlite:///{tmp_path/'dash.db'}"
    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        s.add(Product(kind="pod", title="369 Manifestation", source="existing-catalog",
                      demand_validated=True, metadata_={"blank": "tank top",
                                                        "demand": {"score": 0.42}}))
        s.add(SpendLedger(category="ads", amount_usd=25.0, reference="launch:test"))
        s.add(Decision(kind="kill", actor="engine", target="creative_A",
                       rationale="$25 spent, 0 ATC"))
        s.commit()
    cfg = Config(database_url=url, dashboard_password="secret123")
    return TestClient(create_app(cfg))


def test_requires_auth(tmp_path) -> None:
    c = _client(tmp_path)
    assert c.get("/").status_code == 401
    assert c.get("/", auth=("frio", "wrong")).status_code == 401


def test_authorized_view_renders_data(tmp_path) -> None:
    c = _client(tmp_path)
    r = c.get("/", auth=("frio", "secret123"))
    assert r.status_code == 200
    for needle in ["369 Manifestation", "tank top", "$25.00", "auditor"]:
        assert needle in r.text


def test_healthz_is_open(tmp_path) -> None:
    assert _client(tmp_path).get("/healthz").status_code == 200


def test_no_write_endpoints(tmp_path) -> None:
    # Read-only: nothing should accept POST/PUT/DELETE.
    app = _client(tmp_path).app
    methods = {m for route in app.routes for m in getattr(route, "methods", set())}
    assert methods <= {"GET", "HEAD"}
