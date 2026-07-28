"""Predictive pre-score (Phase 3.5) — advisory, always ungated, no spend."""

from __future__ import annotations

from frio.config import Config
from frio.modules import creation
from frio.modules.prescore import AdTestAIScorer, rank_variants, score_brief
from frio.pipeline import run_phase3_5_prescore

STRONG_VIDEO_BRIEF = {
    "hook": "Stop scrolling. This is your sign.",
    "angle": "manifestation/identity",
    "video_prompt": "10s UGC ad... soft CTA 'tap to shop'.",
}
WEAK_VIDEO_BRIEF = {"hook": "", "angle": "", "video_prompt": "30s ad with no CTA at all."}
NONCOMPLIANT_BRIEF = {
    "hook": "This cures anxiety overnight",
    "angle": "manifestation/identity",
    "video_prompt": "30s ad... guaranteed to manifest abundance.",
}
CAROUSEL_BRIEF = {"hook": "Stop scrolling. This is your sign.",
                  "slides": [{"caption": "hero"}, {"caption": "shop now"}]}


def test_strong_brief_scores_higher_than_weak() -> None:
    strong = score_brief(STRONG_VIDEO_BRIEF, Config())
    weak = score_brief(WEAK_VIDEO_BRIEF, Config())
    assert strong.score > weak.score
    assert strong.engine == "heuristic"  # no LLM configured in tests
    assert strong.recommendation == "test"
    assert weak.recommendation == "revise"


def test_score_is_transparent_and_bounded() -> None:
    r = score_brief(STRONG_VIDEO_BRIEF, Config())
    assert 0.0 <= r.score <= 100.0
    assert all(0.0 <= v <= 100.0 for v in r.dimensions.values())
    assert r.reasons  # every point must be traceable to a stated reason


def test_compliance_violation_penalizes_score() -> None:
    clean = score_brief(STRONG_VIDEO_BRIEF, Config())
    risky = score_brief(NONCOMPLIANT_BRIEF, Config())
    assert risky.score < clean.score
    assert any("Compliance risk" in r for r in risky.reasons)


def test_carousel_brief_scored_via_slides() -> None:
    r = score_brief(CAROUSEL_BRIEF, Config())
    assert r.score > 0
    assert any("CTA" in reason or "closing" in reason for reason in r.reasons)


def test_threshold_is_config_driven() -> None:
    lenient = score_brief(WEAK_VIDEO_BRIEF, Config(prescore_min_to_test=0.0))
    assert lenient.recommendation == "test"
    strict = score_brief(STRONG_VIDEO_BRIEF, Config(prescore_min_to_test=99.9))
    assert strict.recommendation == "revise"


def test_rank_variants_orders_best_first() -> None:
    ranked = rank_variants([WEAK_VIDEO_BRIEF, STRONG_VIDEO_BRIEF, NONCOMPLIANT_BRIEF], Config())
    scores = [r["prescore"]["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0]["brief"] == STRONG_VIDEO_BRIEF


def test_build_brief_variants_uses_distinct_hooks() -> None:
    product = {"title": "369 method tee", "metadata": {"blank": "tee"}}
    hooks = ["Hook A here", "Hook B is different", "Hook C also unique"]
    variants = creation.build_brief_variants(product, hooks, n=3)
    assert len(variants) == 3
    assert [v["hook"] for v in variants] == hooks


def test_adtest_connector_offline_by_default() -> None:
    scorer = AdTestAIScorer(Config())
    assert scorer.available() is False
    import pytest

    with pytest.raises(RuntimeError):
        scorer.score(STRONG_VIDEO_BRIEF)


def test_run_phase3_5_prescore_end_to_end() -> None:
    res = run_phase3_5_prescore(config=Config(database_url="sqlite://"))
    assert res.product and res.ranked
    assert len(res.ranked) <= 3  # default prescore_variants
    scores = [r["prescore"]["score"] for r in res.ranked]
    assert scores == sorted(scores, reverse=True)
