"""Phase 1 pipeline tests (run fully offline)."""

from __future__ import annotations

from frio.config import Config
from frio.connectors.base import RawAd
from frio.modules import competitors as competitors_mod
from frio.modules import strategist
from frio.pipeline import run_phase1


def test_discover_merges_providers_and_ranks_seed_first() -> None:
    comps = competitors_mod.discover("Spiritual Gangster", config=Config())
    assert comps[0]["name"] == "Spiritual Gangster"
    assert comps[0]["similarity_score"] == 1.0
    names = {c["name"] for c in comps}
    # Alo Yoga appears in BOTH similarweb + sparktoro fixtures -> corroborated.
    assert "Alo Yoga" in names
    alo = next(c for c in comps if c["name"] == "Alo Yoga")
    assert alo["relation"] == "aspirational"  # in the aspirational override set
    assert "sparktoro" in alo["signals"]["sources"]
    assert "similarweb" in alo["signals"]["sources"]
    scores = [c["similarity_score"] for c in comps]
    assert scores == sorted(scores, reverse=True)


def test_heuristic_teardown_structure() -> None:
    ad = RawAd(source="creative_center", advertiser="Manifestation Co",
               text="Stop scrolling. This is your sign. The 369 journal. 10k sold.")
    t = strategist.teardown_ad(ad, llm=None)
    assert set(["hook", "pattern_interrupt", "payoff", "angle", "funnel_stage"]) <= set(t)
    assert t["_engine"] == "heuristic"
    assert t["pattern_interrupt"] == "stop scrolling"
    assert t["payoff"] == "social proof + soft CTA"  # has "sold"/"10k"


def test_run_phase1_offline_end_to_end(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p1.db'}"
    res = run_phase1(seed="Spiritual Gangster", config=Config(database_url=url))
    assert res.offline is True
    assert res.competitors and res.ads
    assert res.plan["hook_bank"], "plan should contain hooks mined from teardowns"
    assert len(res.plan["weeks"]) == 4
    assert res.persisted["competitors"] == len(res.competitors)
    # persisted rows are queryable
    from frio.db.base import make_session_factory
    from frio.db.models import Competitor, CompetitorAd

    Session = make_session_factory(url)
    with Session() as s:
        assert s.query(Competitor).count() == len(res.competitors)
        assert s.query(CompetitorAd).count() == len(res.ads)


def test_render_plan_markdown_has_sections() -> None:
    res = run_phase1(seed="Spiritual Gangster", config=Config(database_url="sqlite://"),
                     persist=False)
    md = strategist.render_plan_markdown(res.plan)
    for section in ["Top similar competitors", "Hook bank", "Kill rules", "Weekly cadence"]:
        assert section in md
