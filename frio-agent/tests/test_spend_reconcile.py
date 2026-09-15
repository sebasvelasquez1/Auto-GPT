"""Platform-spend reconciliation — the ledger is our INTENT, not the truth.

GMV Max raises its own daily budget (reportedly up to +50%, several times a day) with
no human approval. A ledger of what we authorized will therefore under-report reality
once a self-optimizing ads product is live. These tests pin the safety behaviour.
"""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.db.base import init_db, make_session_factory
from frio.spend import (
    SpendCapError, gmv_max_worst_case_daily_budget, guard_and_record,
    reconcile_platform_spend,
)


def _session(tmp_path, name):
    url = f"sqlite:///{tmp_path/name}"
    init_db(url)
    return make_session_factory(url)()


def test_no_drift_when_platform_matches_authorized(tmp_path) -> None:
    cfg = Config(daily_spend_cap_usd=100.0)
    with _session(tmp_path, "a.db") as s:
        guard_and_record(s, cfg, category="ads", amount=40.0, per_item_cap=50.0)
        r = reconcile_platform_spend(s, cfg, category="ads", platform_reported_usd=40.0)
    assert r["drift_usd"] == 0.0
    assert r["platform_overspent"] is False
    assert r["cap_breached"] is False


def test_detects_platform_outspending_us_within_cap(tmp_path) -> None:
    """GMV Max raised its own budget: real spend > authorized, but still under cap."""
    cfg = Config(daily_spend_cap_usd=100.0)
    with _session(tmp_path, "b.db") as s:
        guard_and_record(s, cfg, category="ads", amount=40.0, per_item_cap=50.0)
        r = reconcile_platform_spend(s, cfg, category="ads", platform_reported_usd=60.0)
    assert r["platform_overspent"] is True
    assert r["drift_usd"] == 20.0
    assert r["cap_breached"] is False  # surfaced, not fatal — yet


def test_raises_when_platform_breaches_the_daily_cap(tmp_path) -> None:
    """The cap is breached in the real world even though our ledger is clean."""
    cfg = Config(daily_spend_cap_usd=50.0)
    with _session(tmp_path, "c.db") as s:
        guard_and_record(s, cfg, category="ads", amount=30.0, per_item_cap=50.0)
        with pytest.raises(SpendCapError, match="PLATFORM OVERSPEND"):
            reconcile_platform_spend(s, cfg, category="ads", platform_reported_usd=75.0)


def test_zero_cap_means_no_cap_breach_check(tmp_path) -> None:
    """Cap 0 = nothing authorized; reconciliation still reports drift honestly."""
    cfg = Config(daily_spend_cap_usd=0.0)
    with _session(tmp_path, "d.db") as s:
        r = reconcile_platform_spend(s, cfg, category="ads", platform_reported_usd=5.0)
    assert r["platform_overspent"] is True
    assert r["cap_breached"] is False  # cap disabled -> no ceiling to breach


def test_gmv_max_worst_case_disabled_returns_nominal_budget() -> None:
    """Our safe default: auto_budget_enabled=False -> nominal budget, no surprise."""
    assert gmv_max_worst_case_daily_budget(500.0, auto_budget_enabled=False) == 500.0


def test_gmv_max_worst_case_matches_tiktok_own_worked_example() -> None:
    """$500/day at TikTok's own defaults (50% step, limit 10) -> $3,000/day."""
    worst = gmv_max_worst_case_daily_budget(500.0, auto_budget_enabled=True)
    assert worst == 3000.0


def test_gmv_max_worst_case_at_max_settings_is_31x() -> None:
    """300% step x 10 increases = +3000% additive -> 31x the nominal budget."""
    worst = gmv_max_worst_case_daily_budget(
        100.0, auto_budget_enabled=True, increase_percentage=300.0, increase_limit=10)
    assert worst == 3100.0


def test_gmv_max_worst_case_is_additive_not_compounding() -> None:
    """Each step adds a % of the ORIGINAL budget, not of the already-increased one."""
    one_step = gmv_max_worst_case_daily_budget(
        200.0, auto_budget_enabled=True, increase_percentage=50.0, increase_limit=1)
    two_steps = gmv_max_worst_case_daily_budget(
        200.0, auto_budget_enabled=True, increase_percentage=50.0, increase_limit=2)
    # Additive: step size stays constant (100.0 each), not growing off a larger base.
    assert two_steps - one_step == one_step - 200.0
