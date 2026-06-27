"""Phase 2 (POD product origin) tests — run offline."""

from __future__ import annotations

from frio.config import Config
from frio.connectors.demand import demand_score
from frio.modules.product_pod import PODProductOrigin, make_product_origin
from frio.pipeline import run_phase2


def test_demand_score_favors_volume_low_competition() -> None:
    high = demand_score(50000, 0.2)
    low = demand_score(50000, 0.9)
    assert high > low
    assert 0.0 <= high <= 1.0


def test_pod_origin_filters_by_threshold_and_attaches_assets() -> None:
    cfg = Config(demand_threshold=0.2, pipeline="pod")
    products = PODProductOrigin(cfg).discover("spirituality")
    assert products, "expected demand-validated products"
    for p in products:
        assert p.kind == "pod"
        assert p.compliant is True
        assert p.metadata["demand"]["score"] >= cfg.demand_threshold
        assert p.metadata["design_uri"] and p.metadata["mockup_uri"]
    scores = [p.metadata["demand"]["score"] for p in products]
    assert scores == sorted(scores, reverse=True)


def test_high_threshold_filters_everything() -> None:
    cfg = Config(demand_threshold=0.99, pipeline="pod")
    assert PODProductOrigin(cfg).discover("spirituality") == []


def test_make_product_origin_dropship_not_built() -> None:
    import pytest

    with pytest.raises(NotImplementedError):
        make_product_origin(Config(pipeline="dropship"))


def test_run_phase2_persists(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p2.db'}"
    res = run_phase2(niche="spirituality", config=Config(database_url=url, pipeline="pod"))
    assert res.products and res.offline is True
    assert res.persisted["products"] == len(res.products)

    from frio.db.base import make_session_factory
    from frio.db.models import Product

    Session = make_session_factory(url)
    with Session() as s:
        rows = s.query(Product).all()
        assert len(rows) == len(res.products)
        assert all(r.kind == "pod" and r.demand_validated for r in rows)
