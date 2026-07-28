"""Account-safety guardrails — the documented ban vector is volume + similarity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from frio.config import Config
from frio.guardrails import (
    agent_user_agent, check_design_differentiation, check_listing_rate,
    check_material_claims, check_print_black, preflight_listing, similarity,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
CFG = Config()


def test_listing_rate_limit_blocks_bulk_velocity() -> None:
    recent = [NOW - timedelta(hours=h) for h in range(5)]  # 5 in last 24h, cap 5
    v = check_listing_rate(recent, max_per_day=CFG.guard_max_listings_per_day, now=NOW)
    assert not v.ok and "rate limit" in v.reasons[0].lower()


def test_listing_rate_ignores_older_than_24h() -> None:
    old = [NOW - timedelta(days=2, hours=h) for h in range(50)]
    assert check_listing_rate(old, max_per_day=5, now=NOW).ok


def test_near_duplicate_designs_rejected() -> None:
    existing = ["Moon phases spiritual tee for the modern mystic"]
    dup = check_design_differentiation(
        "Moon phases spiritual tee for the modern mystic", existing, max_similarity=0.7)
    assert not dup.ok and "similar" in dup.reasons[0].lower()

    distinct = check_design_differentiation(
        "Grounding affirmations crewneck in earth tones", existing, max_similarity=0.7)
    assert distinct.ok


def test_similarity_is_symmetric_and_bounded() -> None:
    a, b = "stay grounded daily ritual tee", "daily ritual grounding sweatshirt"
    assert similarity(a, b) == similarity(b, a)
    assert 0.0 <= similarity(a, b) <= 1.0
    assert similarity(a, a) == 1.0


def test_material_claims_flagged() -> None:
    """Documented return driver: buyers expected UV-reactive fabric."""
    v = check_material_claims("Glowing moon phases tee")
    assert not v.ok and "glow" in v.reasons[0]
    assert check_material_claims("Calm moon phases tee").ok


def test_near_black_flagged() -> None:
    assert not check_print_black("design uses #0a0a0a on dark garment").ok
    assert check_print_black("design uses #000000 on dark garment").ok


def test_agent_self_identifies_as_automated() -> None:
    """Amazon BSA s19 requires automated agents to identify themselves as such."""
    ua = agent_user_agent()
    assert "FrioAgent" in ua and "automated" in ua.lower()


def test_preflight_collects_every_failure() -> None:
    recent = [NOW - timedelta(hours=h) for h in range(5)]
    v = preflight_listing("Glowing moon phases tee", ["Glowing moon phases tee"],
                          recent, CFG, now=NOW)
    assert not v.ok
    assert len(v.reasons) >= 3  # rate + similarity + material claim


def test_preflight_passes_a_clean_listing() -> None:
    v = preflight_listing("Grounding affirmations crewneck in earth tones",
                          ["Moon phases spiritual tee"], [], CFG, now=NOW)
    assert v.ok and not v.reasons


def test_kill_never_maps_to_irreversible_delete() -> None:
    """TikTok: a deleted campaign's status cannot be modified. Kills must be reversible."""
    assert CFG.ads_kill_operation == "DISABLE"
    assert CFG.ads_kill_operation != "DELETE"
