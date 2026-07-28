"""Spend-cap enforcement against the append-only spend ledger.

The hard rule: NO capability may spend money beyond the configured caps. Caps
default to 0, which means *only zero-cost (offline) actions pass* until the user
explicitly raises them — a fail-safe default. The LLM can never override this;
it is plain deterministic code.

⚠️ CRITICAL LIMITATION this module alone cannot fix (research 2026-07-28):
the ledger records what WE authorized. TikTok's GMV Max **raises its own daily budget
by up to 50%, reportedly several times in one day, with no human approval**. Meta
Advantage+ and Google PMax behave similarly. So once a live ads platform is wired, the
platform is an EXTERNAL ACTOR that can spend beyond anything we authorized, and a
ledger of our own intentions will silently under-report reality.

``reconcile_platform_spend`` closes that gap: it compares authorized spend against the
platform's REPORTED actual spend and raises when the platform has outrun us. Any live
ads connector MUST call it on every polling cycle. Trusting the ledger alone once
GMV Max is on would be a false sense of safety.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from .config import Config
from .db.models import SpendLedger


class SpendCapError(RuntimeError):
    """Raised when an action would exceed a configured spend cap."""


def spent_today(session, category: str) -> float:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = session.execute(
        select(func.coalesce(func.sum(SpendLedger.amount_usd), 0.0)).where(
            SpendLedger.category == category, SpendLedger.created_at >= start
        )
    ).scalar_one()
    return float(total)


def guard_and_record(session, config: Config, *, category: str, amount: float,
                     reference: str | None = None, per_item_cap: float | None = None) -> None:
    """Raise if ``amount`` breaches the per-item or daily cap; else append a ledger row.

    ``per_item_cap`` may be passed explicitly (e.g. per-image vs per-clip); if None
    it is derived from the category. Daily caps aggregate per category, so video and
    image renders share the "creation" daily budget.
    """
    if amount < 0:
        raise SpendCapError("negative spend amounts are not allowed")

    if per_item_cap is None:
        per_item_cap = (
            config.per_clip_cost_cap_usd if category == "creation"
            else config.per_campaign_spend_cap_usd
        )
    if amount > per_item_cap:
        raise SpendCapError(
            f"{category} cost ${amount:.2f} exceeds per-item cap ${per_item_cap:.2f} "
            f"(raise FRIO_{'PER_CLIP_COST' if category == 'creation' else 'PER_CAMPAIGN_SPEND'}_CAP_USD)"
        )

    projected = spent_today(session, category) + amount
    if projected > config.daily_spend_cap_usd:
        raise SpendCapError(
            f"{category} daily spend ${projected:.2f} would exceed cap "
            f"${config.daily_spend_cap_usd:.2f} (raise FRIO_DAILY_SPEND_CAP_USD)"
        )

    session.add(SpendLedger(category=category, amount_usd=amount, reference=reference))


def authorized_today(session, category: str) -> float:
    """Alias for readability at call sites that also fetch platform actuals."""
    return spent_today(session, category)


def reconcile_platform_spend(session, config: Config, *, category: str,
                             platform_reported_usd: float,
                             tolerance_usd: float = 0.01) -> dict:
    """Compare what we authorized against what the platform actually spent.

    Returns a dict describing the drift. Raises ``SpendCapError`` when the platform's
    actual spend exceeds the daily cap — regardless of what we authorized — because at
    that point the cap has been breached in the real world even if our ledger is clean.

    This exists because self-optimizing ad products (GMV Max, Advantage+, PMax) can
    increase budgets on their own. The ledger is our intent; this is the truth.
    """
    authorized = spent_today(session, category)
    drift = platform_reported_usd - authorized
    cap = config.daily_spend_cap_usd
    result = {
        "category": category,
        "authorized_usd": round(authorized, 4),
        "platform_reported_usd": round(platform_reported_usd, 4),
        "drift_usd": round(drift, 4),
        "platform_overspent": drift > tolerance_usd,
        "daily_cap_usd": cap,
        "cap_breached": cap > 0 and platform_reported_usd > cap + tolerance_usd,
    }
    if result["cap_breached"]:
        raise SpendCapError(
            f"PLATFORM OVERSPEND: {category} actual ${platform_reported_usd:.2f} exceeds "
            f"the daily cap ${cap:.2f} (we authorized ${authorized:.2f}). Self-optimizing "
            f"ad products raise their own budgets — pause the campaign now.")
    return result
