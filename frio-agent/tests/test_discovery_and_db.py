"""Competitor-discovery stub + DB schema smoke tests."""

from __future__ import annotations

from frio.db.base import init_db, make_session_factory
from frio.db.models import Competitor, CompetitorAd
from frio.modules.competitors import discover


def test_discover_ranks_spiritual_gangster_seed() -> None:
    results = discover(seed="Spiritual Gangster", limit=10)
    assert results, "expected at least the seed brand"
    # Sorted by similarity desc, seed brand first at 1.0
    assert results[0]["name"] == "Spiritual Gangster"
    assert results[0]["similarity_score"] == 1.0
    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert {r["relation"] for r in results} <= {"direct", "indirect", "aspirational"}


def test_discover_unknown_seed_returns_seed_itself() -> None:
    results = discover(seed="Some Unknown Brand")
    assert results[0]["name"] == "Some Unknown Brand"


def test_schema_create_and_insert(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'frio_test.db'}"
    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        comp = Competitor(name="Spiritual Gangster", relation="direct", similarity_score=1.0)
        comp.ads.append(CompetitorAd(source="creative_center", teardown={"hook": "POV"}))
        s.add(comp)
        s.commit()
        loaded = s.query(Competitor).filter_by(name="Spiritual Gangster").one()
        assert loaded.ads[0].teardown["hook"] == "POV"
