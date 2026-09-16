"""The single-ad-account pin.

Why this exists: the seller's TikTok login can reach MORE THAN ONE ad account — this
project's owner has a personal Colombian account and a separate US-company account,
because TikTok Shop is US-only for them. An MCP grant covers every account that login
can see, so "we will spend on the right account" must be enforced by code, not assumed.
"""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.connectors.tiktok_ads import TikTokAdsConnector
from frio.guardrails import WrongAdAccountError, require_pinned_ad_account

LIVE_PINNED = {"tiktok_ads_api_key": "k", "tiktok_ads_advertiser_id": "7000000000000000001"}


def test_live_action_without_a_pin_is_refused() -> None:
    """The dangerous default. A live token with no pin could land spend anywhere."""
    conn = TikTokAdsConnector(Config(tiktok_ads_api_key="k"))
    with pytest.raises(WrongAdAccountError, match="no pinned ad account"):
        conn.launch_campaign("c", 5.0)


def test_live_action_on_a_different_account_is_refused() -> None:
    conn = TikTokAdsConnector(Config(**LIVE_PINNED))
    with pytest.raises(WrongAdAccountError, match="pinned to '7000000000000000001'"):
        conn.launch_campaign("c", 5.0, advertiser_id="7999999999999999999")


def test_every_money_touching_method_is_guarded_not_just_launch() -> None:
    """A pin enforced on only one entry point is not a pin."""
    conn = TikTokAdsConnector(Config(**LIVE_PINNED))
    other = "7999999999999999999"
    with pytest.raises(WrongAdAccountError):
        conn.pause_campaign("ext", advertiser_id=other)
    with pytest.raises(WrongAdAccountError):
        conn.set_budget("ext", 50.0, advertiser_id=other)


def test_mismatch_is_rejected_even_offline_so_miswiring_surfaces_in_tests() -> None:
    conn = TikTokAdsConnector(Config(tiktok_ads_advertiser_id="pinned"))
    with pytest.raises(WrongAdAccountError):
        conn.launch_campaign("c", 5.0, advertiser_id="other")


def test_offline_pipeline_still_runs_with_no_pin_at_all() -> None:
    """Project rule: the pipeline always runs on fixtures with no credentials."""
    conn = TikTokAdsConnector(Config())
    assert conn.launch_campaign("c", 5.0).startswith("ttc-offline-")
    assert conn.pause_campaign("ext")["status"] == "paused_offline"
    assert conn.set_budget("ext", 5.0)["status"] == "budget_set_offline"


def test_matching_account_and_implicit_pin_both_resolve_to_the_pin() -> None:
    assert require_pinned_ad_account("a", pinned="a", live=True) == "a"
    assert require_pinned_ad_account(None, pinned="a", live=True) == "a"
