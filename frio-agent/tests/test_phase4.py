"""Phase 4 (optimize engine) tests — the money brain gets the heaviest coverage."""

from __future__ import annotations

from frio.config import Config
from frio.metrics import EntityMetrics
from frio.modules.optimize import cadence_focus, evaluate
from frio.pipeline import run_phase4


def _m(**kw) -> EntityMetrics:
    base = dict(entity_type="creative", entity_id="c", spend_usd=0.0, impressions=0,
                clicks=0, add_to_carts=0, purchases=0, revenue_usd=0.0)
    base.update(kw)
    return EntityMetrics(**base)


CFG = Config()


def test_kill_on_spend_without_atc() -> None:
    p = evaluate(_m(spend_usd=25, impressions=5000, clicks=10, add_to_carts=0), CFG)
    assert p.action == "kill" and p.auto_executable is True
    assert p.budget_change_pct == -1.0
    assert "0 add-to-carts" in p.reason


def test_kill_on_low_ctr() -> None:
    # CTR 0.4% over 2000 impressions, but has 1 ATC (so not the no-ATC rule)
    p = evaluate(_m(spend_usd=15, impressions=2000, clicks=8, add_to_carts=1), CFG)
    assert p.action == "kill" and "CTR" in p.reason


def test_no_ctr_kill_below_min_impressions() -> None:
    # 0.5% CTR but only 800 impressions -> not enough data to kill on CTR
    p = evaluate(_m(spend_usd=5, impressions=800, clicks=4, add_to_carts=1), CFG)
    assert p.action == "hold"


def test_scale_requires_approval_and_purchases() -> None:
    p = evaluate(_m(spend_usd=50, impressions=4000, clicks=120, add_to_carts=30,
                    purchases=15, revenue_usd=300), CFG)
    assert p.action == "scale"
    assert p.auto_executable is False  # increasing spend needs human sign-off
    assert p.budget_change_pct == CFG.opt_scale_budget_step_pct


def test_high_mer_but_too_few_purchases_holds() -> None:
    p = evaluate(_m(spend_usd=8, impressions=900, clicks=20, add_to_carts=3,
                    purchases=2, revenue_usd=80), CFG)
    assert p.action == "hold"  # below opt_scale_min_purchases


def test_kill_takes_priority_over_scale() -> None:
    # great MER but $25 spent with 0 ATC -> safety kill wins
    p = evaluate(_m(spend_usd=25, impressions=5000, clicks=10, add_to_carts=0,
                    purchases=0, revenue_usd=0), CFG)
    assert p.action == "kill"


def test_cpa_kill_when_target_set() -> None:
    cfg = Config(opt_target_cpa_usd=10.0, opt_kill_cpa_multiple=3.0)
    # CPA = 100/2 = $50 > 3x$10
    p = evaluate(_m(spend_usd=100, impressions=5000, clicks=200, add_to_carts=10,
                    purchases=2, revenue_usd=120), cfg)
    assert p.action == "kill" and "CPA" in p.reason


def test_thresholds_come_from_config() -> None:
    strict = Config(opt_kill_spend_no_atc_usd=5.0)
    p = evaluate(_m(spend_usd=6, impressions=100, clicks=1, add_to_carts=0), strict)
    assert p.action == "kill"  # $6 >= $5 strict threshold


def test_cadence_focus() -> None:
    assert "Kill bottom 80%" in cadence_focus(2)
    assert cadence_focus(99)  # steady-state fallback


def test_run_phase4_demo_end_to_end(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p4.db'}"
    res = run_phase4(config=Config(database_url=url), seed_demo=True)
    # demo set: A kill, B kill, C scale, D hold
    assert res.kills == 2 and res.scales == 1 and res.holds == 1
    assert res.auto_applied == 2  # the two kills
    assert res.awaiting_approval == 1  # the scale

    from frio.db.base import make_session_factory
    from frio.db.models import Decision

    Session = make_session_factory(url)
    with Session() as s:
        kinds = [d.kind for d in s.query(Decision).all()]
        assert kinds.count("kill") == 2 and kinds.count("scale") == 1
