"""Fatigue, scaling-plateau and product-lifecycle (harvest) detection tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from frio.config import Config
from frio.db.base import init_db, make_session_factory
from frio.db.models import MetricsDaily
from frio.modules.analyzer import analyze_listing_from_db, cost_structure_from, lifecycle_stage
from frio.modules.optimize import detect_fatigue, detect_scaling_plateau, propose_all

CFG = Config()


def _day(impressions=2000, clicks=40, spend=10.0, revenue=0.0, frequency=1.5,
         purchases=0) -> dict:
    return {"day": None, "impressions": impressions, "clicks": clicks,
            "spend_usd": spend, "revenue_usd": revenue, "frequency": frequency,
            "add_to_carts": 0, "purchases": purchases}


# --- creative fatigue --------------------------------------------------------

def test_fatigue_on_ctr_collapse_vs_own_baseline() -> None:
    # baseline CTR 2%, recent 3 days CTR 1% (down 50% > 20% threshold)
    series = [_day(clicks=40) for _ in range(7)] + [_day(clicks=20) for _ in range(3)]
    reason = detect_fatigue(series, CFG)
    assert reason and "below its own baseline" in reason


def test_no_fatigue_when_ctr_stable() -> None:
    series = [_day(clicks=40) for _ in range(10)]
    assert detect_fatigue(series, CFG) is None


def test_fatigue_on_high_frequency() -> None:
    series = [_day() for _ in range(7)] + [_day(frequency=4.2) for _ in range(3)]
    reason = detect_fatigue(series, CFG)
    assert reason and "saturated" in reason


def test_fatigue_needs_history_and_volume() -> None:
    assert detect_fatigue([_day() for _ in range(3)], CFG) is None  # too short
    tiny = [_day(impressions=50, clicks=1) for _ in range(10)]
    assert detect_fatigue(tiny, CFG) is None  # not enough impressions to judge


# --- scaling plateau (diminishing returns) -----------------------------------

def test_plateau_spend_up_mer_down() -> None:
    base = [_day(spend=50, revenue=200) for _ in range(4)]   # MER 4.0
    recent = [_day(spend=100, revenue=250) for _ in range(4)]  # MER 2.5 (-38%)
    reason = detect_scaling_plateau(base + recent, CFG)
    assert reason and "diminishing returns" in reason


def test_no_plateau_when_mer_holds_while_scaling() -> None:
    base = [_day(spend=50, revenue=200) for _ in range(4)]
    recent = [_day(spend=100, revenue=400) for _ in range(4)]  # MER holds at 4.0
    assert detect_scaling_plateau(base + recent, CFG) is None


def test_propose_all_vetoes_scale_on_plateau(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'p.db'}"
    init_db(url)
    Session = make_session_factory(url)
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with Session() as s:
        # A would-be scale winner (MER 5, purchases 20) whose marginal MER collapses.
        for i in range(4):
            s.add(MetricsDaily(entity_type="creative", entity_id="c1",
                               day=start + timedelta(days=i), spend_usd=50,
                               impressions=2000, clicks=60, add_to_carts=20,
                               purchases=5, revenue_usd=400, frequency=1.5))
        for i in range(4, 8):
            s.add(MetricsDaily(entity_type="creative", entity_id="c1",
                               day=start + timedelta(days=i), spend_usd=100,
                               impressions=4000, clicks=120, add_to_carts=20,
                               purchases=5, revenue_usd=250, frequency=1.6))
        s.commit()
        proposals = propose_all(s, CFG, "creative")
    assert len(proposals) == 1
    assert proposals[0].action == "hold"
    assert "Stop scaling" in proposals[0].reason


def test_propose_all_flags_fatigued_creative(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'f.db'}"
    init_db(url)
    Session = make_session_factory(url)
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with Session() as s:
        # Profitable creative (won't be killed) whose CTR then collapses 50%.
        for i in range(7):
            s.add(MetricsDaily(entity_type="creative", entity_id="c2",
                               day=start + timedelta(days=i), spend_usd=20,
                               impressions=2000, clicks=40, add_to_carts=10,
                               purchases=4, revenue_usd=160, frequency=1.5))
        for i in range(7, 10):
            s.add(MetricsDaily(entity_type="creative", entity_id="c2",
                               day=start + timedelta(days=i), spend_usd=20,
                               impressions=2000, clicks=20, add_to_carts=5,
                               purchases=2, revenue_usd=80, frequency=1.5))
        s.commit()
        proposals = propose_all(s, CFG, "creative")
    assert proposals[0].action == "refresh"
    assert proposals[0].auto_executable is False  # replacing creative costs money
    assert "fatigue" in proposals[0].reason.lower()


# --- product lifecycle: harvest ----------------------------------------------

def test_lifecycle_declining_and_seasonality_note() -> None:
    stage, note = lifecycle_stage([10, 20, 30, 25, 18, 12], CFG)  # 3 falling weeks
    assert stage == "declining"
    assert "VERIFY it isn't seasonality" in note  # short history guard

    stage, _ = lifecycle_stage([10, 20, 30, 32, 31, 33], CFG)
    assert stage in ("growing", "steady")
    assert lifecycle_stage([5, 6], CFG)[0] == "insufficient"


def test_harvest_verdict_profitable_but_declining(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'h.db'}"
    init_db(url)
    Session = make_session_factory(url)
    cfg = Config(database_url=url)
    start = datetime(2026, 3, 2, tzinfo=timezone.utc)  # a Monday
    weekly = [30, 24, 18, 12]  # peak then 3 straight declining weeks
    with Session() as s:
        for w, units in enumerate(weekly):
            s.add(MetricsDaily(entity_type="product", entity_id="L1",
                               day=start + timedelta(weeks=w), purchases=units,
                               revenue_usd=units * 30.0, spend_usd=units * 3.0))
        s.commit()

    cs = cost_structure_from(cfg, price=30.0, product_cost=9.0, fulfillment_cost=5.0)
    v = analyze_listing_from_db("L1", cs, config=cfg, database_url=url)
    assert v.decision == "harvest"
    assert v.pnl["net_profit"] > 0  # still profitable — milk it, don't kill it
    assert any("Lifecycle" in r for r in v.reasons)
