"""Spend-cap enforcement against the append-only spend ledger.

The hard rule: NO capability may spend money beyond the configured caps. Caps
default to 0, which means *only zero-cost (offline) actions pass* until the user
explicitly raises them — a fail-safe default. The LLM can never override this;
it is plain deterministic code.
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
