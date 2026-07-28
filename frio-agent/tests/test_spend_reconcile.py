"""Platform-spend reconciliation — the ledger is our INTENT, not the truth.

GMV Max raises its own daily budget (reportedly up to +50%, several times a day) with
no human approval. A ledger of what we authorized will therefore under-report reality
once a self-optimizing ads product is live. These tests pin the safety behaviour.
"""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.db.base import init_db, make_session_factory
from frio.spend import SpendCapError, guard_and_record, reconcile_platform_spend


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
