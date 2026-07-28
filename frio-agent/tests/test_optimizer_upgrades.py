"""Track-2 research upgrades: statistical kills + Thompson allocation + claims scan."""

from __future__ import annotations

from frio.compliance import check_claims, has_ai_disclosure, review_creative
from frio.config import Config
from frio.metrics import EntityMetrics
from frio.modules.optimize import evaluate
from frio.pipeline import run_phase6_loop
from frio.stats import thompson_allocation, wilson_interval, wilson_upper_bound


def _m(**kw) -> EntityMetrics:
    base = dict(entity_type="creative", entity_id="c", spend_usd=0.0, impressions=0,
                clicks=0, add_to_carts=0, purchases=0, revenue_usd=0.0)
    base.update(kw)
    return EntityMetrics(**base)


# --- stats -----------------------------------------------------------------

def test_wilson_upper_above_point_and_bounded() -> None:
    lo, hi = wilson_interval(8, 2000)
    assert 0.0 <= lo <= 8 / 2000 <= hi <= 1.0
    # small sample => wide interval (more uncertainty)
    assert wilson_upper_bound(1, 10) > wilson_upper_bound(100, 1000)


def test_thompson_allocation_sums_and_is_seeded() -> None:
    arms = [("a", 30, 100), ("b", 2, 100)]
    alloc = thompson_allocation(arms, 100.0, seed=0)
    assert set(alloc) == {"a", "b"}
    assert abs(sum(alloc.values()) - 100.0) < 0.05
    assert thompson_allocation(arms, 100.0, seed=0) == alloc  # deterministic
    assert thompson_allocation([], 100.0) == {}


# --- statistically-guarded CTR kill ----------------------------------------

BORDERLINE = dict(spend_usd=8, impressions=1000, clicks=9, add_to_carts=1)  # CTR 0.9%


def test_statistical_mode_holds_borderline_small_sample() -> None:
    # 0.9% point estimate < 1% floor, but the 95% upper bound is still above it
    p = evaluate(_m(**BORDERLINE), Config(opt_use_statistical_ctr=True))
    assert p.action == "hold"


def test_nonstatistical_mode_kills_borderline() -> None:
    p = evaluate(_m(**BORDERLINE), Config(opt_use_statistical_ctr=False))
    assert p.action == "kill"


def test_statistical_mode_still_kills_clear_loser() -> None:
    # 0.4% over 2000 impressions: confidently below floor
    p = evaluate(_m(spend_usd=15, impressions=2000, clicks=8, add_to_carts=1),
                 Config(opt_use_statistical_ctr=True))
    assert p.action == "kill" and "upper bound" in p.reason


# --- Thompson allocation wired into the closed loop ------------------------

def test_closed_loop_suggests_scale_budget(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'loop.db'}"
    cfg = Config(ads_live_enabled=True, seller_approved=True, database_url=url,
                 opt_scale_pool_usd=50.0)
    res = run_phase6_loop(config=cfg, seed_demo=True)
    assert res["awaiting_approval"] == 1
    scale = res["pending_scales"][0]
    # single winner gets the whole pool (normalized)
    assert scale["suggested_budget_usd"] == 50.0


# --- claims compliance scanner (Track 1, kept) -----------------------------

def test_claims_flags_prohibited() -> None:
    assert check_claims("Lose weight fast with this tea")
    assert check_claims("dramatic before & after results")
    assert check_claims("cures anxiety overnight")
    assert check_claims("guaranteed to manifest abundance")


def test_clean_creative_passes() -> None:
    rep = review_creative("Daily reminder to stay grounded. Soft cotton tee.",
                          requires_ai_disclosure=False)
    assert rep["ok"] is True and rep["violations"] == []


def test_ai_disclosure_detection() -> None:
    assert has_ai_disclosure("This ad is AI-generated")
    rep = review_creative("no disclosure here", requires_ai_disclosure=True)
    assert rep["needs_ai_disclosure"] is True and rep["ok"] is False
