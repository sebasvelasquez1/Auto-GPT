"""Phase 6 (live ads + closed loop) tests — spend safety is the whole point."""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.modules import ads
from frio.pipeline import run_phase6_launch, run_phase6_loop
from frio.spend import SpendCapError

LIVE = dict(ads_live_enabled=True, seller_approved=True,
            per_campaign_spend_cap_usd=10.0, daily_spend_cap_usd=20.0)


def test_launch_blocked_when_ads_disabled() -> None:
    with pytest.raises(PermissionError):
        ads.launch_campaign("c", 5.0, Config(ads_live_enabled=False, seller_approved=True),
                            approve=True)


def test_launch_requires_both_flags() -> None:
    with pytest.raises(PermissionError):
        ads.launch_campaign("c", 5.0, Config(ads_live_enabled=True, seller_approved=False),
                            approve=True)


def test_launch_requires_approval() -> None:
    with pytest.raises(PermissionError):
        ads.launch_campaign("c", 5.0, Config(**LIVE), approve=False)


def test_launch_blocked_over_per_campaign_cap(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'a.db'}"
    cfg = Config(**LIVE, database_url=url)
    with pytest.raises(SpendCapError):  # $15 > $10 per-campaign cap
        ads.launch_campaign("c", 15.0, cfg, approve=True, database_url=url)


def test_launch_succeeds_and_records_spend(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'b.db'}"
    cfg = Config(**LIVE, database_url=url)
    out = ads.launch_campaign("frio-test", 5.0, cfg, approve=True, database_url=url)
    assert out["campaign_id"].startswith("ttc-offline-")

    from frio.db.base import make_session_factory
    from frio.db.models import Campaign, SpendLedger

    Session = make_session_factory(url)
    with Session() as s:
        assert s.query(Campaign).count() == 1
        assert s.query(SpendLedger).filter_by(category="ads").one().amount_usd == 5.0


def test_daily_cap_blocks_second_launch(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c.db'}"
    cfg = Config(**LIVE, database_url=url)  # daily cap $20, per-campaign $10
    ads.launch_campaign("a", 9.0, cfg, approve=True, database_url=url)
    ads.launch_campaign("b", 9.0, cfg, approve=True, database_url=url)  # day=18
    with pytest.raises(SpendCapError):  # +9 => 27 > 20
        ads.launch_campaign("c", 9.0, cfg, approve=True, database_url=url)


def test_scale_blocked_over_cap(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'d.db'}"
    cfg = Config(**LIVE, database_url=url)
    out = ads.launch_campaign("a", 5.0, cfg, approve=True, database_url=url)
    with pytest.raises(SpendCapError):  # $12 > $10 per-campaign cap
        ads.scale_campaign(out["campaign_id"], 12.0, cfg, approve=True, database_url=url)


def test_scale_increases_budget_within_caps(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'e.db'}"
    cfg = Config(**LIVE, database_url=url)
    out = ads.launch_campaign("a", 5.0, cfg, approve=True, database_url=url)
    res = ads.scale_campaign(out["campaign_id"], 8.0, cfg, approve=True, database_url=url)
    assert res["old_budget"] == 5.0 and res["new_budget"] == 8.0


def test_closed_loop_auto_kills_and_surfaces_scales(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'loop.db'}"
    cfg = Config(**LIVE, database_url=url)
    res = run_phase6_loop(config=cfg, seed_demo=True)
    # demo metrics: 2 kills, 1 scale (needs approval), 1 hold
    assert res["applied_kills"] == 2
    assert res["awaiting_approval"] == 1

    from frio.db.base import make_session_factory
    from frio.db.models import Decision

    Session = make_session_factory(url)
    with Session() as s:
        kinds = [d.kind for d in s.query(Decision).all()]
        assert kinds.count("kill_applied") == 2  # auto
        assert kinds.count("scale_proposed") == 1  # awaiting human


def test_run_phase6_launch_gate_message(tmp_path) -> None:
    res = run_phase6_launch("c", 5.0, approve=True,
                            config=Config(database_url=f"sqlite:///{tmp_path/'g.db'}"))
    assert res.campaign_id is None and "disabled" in (res.gate_message or "")
