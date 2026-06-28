"""Capability registry + gating tests (the gating is load-bearing for spend safety)."""

from __future__ import annotations

from frio.capabilities import REGISTRY, load_all_capabilities
from frio.config import Config


def setup_module(_module) -> None:
    load_all_capabilities()


def test_research_capability_is_ungated() -> None:
    cfg = Config()  # all gates off by default
    cap = REGISTRY.get("competitors.discover")
    assert cap.is_enabled(cfg) is True
    assert cap.category == "research"


def test_ads_capability_gated_off_by_default() -> None:
    cfg = Config(ads_live_enabled=False, seller_approved=False)
    cap = REGISTRY.get("ads.launch_campaign")
    assert cap.is_enabled(cfg) is False
    assert cap.disabled_reason  # must explain why


def test_ads_capability_requires_both_flags() -> None:
    cap = REGISTRY.get("ads.launch_campaign")
    assert cap.is_enabled(Config(ads_live_enabled=True, seller_approved=False)) is False
    assert cap.is_enabled(Config(ads_live_enabled=False, seller_approved=True)) is False
    assert cap.is_enabled(Config(ads_live_enabled=True, seller_approved=True)) is True


def test_enabled_filter() -> None:
    cfg = Config()
    enabled_names = {c.name for c in REGISTRY.enabled(cfg)}
    assert "competitors.discover" in enabled_names
    assert "ads.launch_campaign" not in enabled_names
