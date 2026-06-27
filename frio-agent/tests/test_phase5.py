"""Phase 5 (commerce / fulfillment) tests — gating + HITL are the point."""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.connectors.fulfillment import (
    CJFulfillment,
    PrintfulFulfillment,
    make_fulfillment,
)
from frio.interfaces import ProductCandidate
from frio.modules import commerce
from frio.pipeline import run_phase5_publish

POD_PRODUCT = {"external_id": None, "title": "369 method tee", "source": "ai-design",
               "kind": "pod", "metadata": {"blank": "tee"}, "compliant": True}


def test_make_fulfillment_selects_backend() -> None:
    assert isinstance(make_fulfillment(Config(pipeline="pod")), PrintfulFulfillment)
    assert isinstance(make_fulfillment(Config(pipeline="dropship")), CJFulfillment)


def test_publish_blocked_when_not_seller_approved() -> None:
    with pytest.raises(PermissionError):
        commerce.publish_product(POD_PRODUCT, Config(seller_approved=False), approve=True)


def test_publish_blocked_without_approval() -> None:
    with pytest.raises(PermissionError):
        commerce.publish_product(POD_PRODUCT, Config(seller_approved=True), approve=False)


def test_publish_succeeds_when_gated_open(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c.db'}"
    cfg = Config(seller_approved=True, pipeline="pod", database_url=url)
    out = commerce.publish_product(POD_PRODUCT, cfg, approve=True, database_url=url)
    assert out["listing_id"].startswith("printful-offline-")
    assert out["provider"] == "printful"

    from frio.db.base import make_session_factory
    from frio.db.models import Decision

    Session = make_session_factory(url)
    with Session() as s:
        assert s.query(Decision).filter_by(kind="publish").count() == 1


def test_dropship_non_compliant_refused() -> None:
    bad = ProductCandidate(external_id=None, title="arbitrage gadget", source="aliexpress",
                           kind="dropship", compliant=False)
    with pytest.raises(PermissionError):
        CJFulfillment(Config(cj_api_key=None)).publish_product(bad)


def test_sync_sales_writes_metrics(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'s.db'}"
    cfg = Config(seller_approved=True, database_url=url)
    out = commerce.sync_sales("printful-offline-x", cfg, database_url=url)
    assert out["purchases"] == 3 and out["revenue_usd"] == 75.0

    from frio.db.base import make_session_factory
    from frio.db.models import MetricsDaily

    Session = make_session_factory(url)
    with Session() as s:
        row = s.query(MetricsDaily).filter_by(entity_type="product").one()
        assert row.purchases == 3 and row.revenue_usd == 75.0


def test_sync_sales_gated() -> None:
    with pytest.raises(PermissionError):
        commerce.sync_sales("x", Config(seller_approved=False))


def test_run_phase5_gate_blocks_by_default(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p5.db'}"
    res = run_phase5_publish(config=Config(database_url=url), approve=True)  # seller not approved
    assert res.listing_id is None
    assert "disabled" in (res.gate_message or "")


def test_run_phase5_publishes_when_approved(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p5b.db'}"
    cfg = Config(seller_approved=True, pipeline="pod", database_url=url)
    res = run_phase5_publish(config=cfg, approve=True)
    assert res.listing_id and res.provider == "printful"
