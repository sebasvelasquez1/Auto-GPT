"""Phase 2 (POD product origin) tests — existing designs x competitor-recommended formats."""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.connectors.demand import demand_score
from frio.modules.product_pod import (
    GeneratedDesignOrigin,
    PODProductOrigin,
    make_product_origin,
    recommend_blanks,
)
from frio.pipeline import run_phase2


def test_demand_score_favors_volume_low_competition() -> None:
    assert demand_score(50000, 0.2) > demand_score(50000, 0.9)
    assert 0.0 <= demand_score(50000, 0.2) <= 1.0


def test_recommend_blanks_from_competitor_signal() -> None:
    # The seller's insight: competitor best-sellers => tank tops beat tees.
    blanks = recommend_blanks("spirituality")
    assert blanks[0]["blank"] == "tank top"
    scores = [b["score"] for b in blanks]
    assert scores == sorted(scores, reverse=True)


def test_pod_origin_uses_existing_designs_and_top_blank() -> None:
    cfg = Config(pipeline="pod")
    products = PODProductOrigin(cfg).discover("spirituality")
    assert products, "expected the seller's existing designs"
    for p in products:
        assert p.kind == "pod" and p.source == "existing-catalog"
        assert p.metadata["design_id"] and p.metadata["design_uri"]  # OUR design
        assert p.metadata["blank"] == "tank top"                     # top recommended format
        assert p.metadata["mockup_uri"]
    # ranked by theme demand
    scores = [p.metadata["demand"]["score"] for p in products]
    assert scores == sorted(scores, reverse=True)


def test_scale_winner_to_formats() -> None:
    cfg = Config(pipeline="pod")
    from frio.modules.product_pod import scale_winner_to_formats

    cands = scale_winner_to_formats("d-369", "spirituality", cfg, top=3)
    assert len(cands) == 3
    blanks = [c.metadata["blank"] for c in cands]
    assert blanks == ["tank top", "muscle tee", "tee"]  # competitor-ranked formats
    for c in cands:
        assert c.source == "scaled-winner"
        assert c.metadata["design_id"] == "d-369"  # same winning design
        assert c.metadata["scaled_from_winner"] is True
        assert c.metadata["mockup_uri"]


def test_scale_winner_unknown_design_returns_empty() -> None:
    from frio.modules.product_pod import scale_winner_to_formats

    assert scale_winner_to_formats("nope", "spirituality", Config()) == []


def test_generated_origin_is_deferred() -> None:
    with pytest.raises(NotImplementedError):
        GeneratedDesignOrigin().discover("spirituality")


def test_make_product_origin_dropship_not_built() -> None:
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
        assert all(r.kind == "pod" for r in rows)
