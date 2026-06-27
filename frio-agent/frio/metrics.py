"""Deterministic metric computation over the metrics_daily table.

Pure math, no LLM — these numbers drive money decisions, so they must be exact
and auditable. Aggregates raw daily rows into per-entity totals + derived rates
(CTR, CPA, MER, CPC, ATC rate).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from .db.models import MetricsDaily


@dataclass
class EntityMetrics:
    entity_type: str
    entity_id: str
    spend_usd: float = 0.0
    impressions: int = 0
    clicks: int = 0
    add_to_carts: int = 0
    purchases: int = 0
    revenue_usd: float = 0.0

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        return self.spend_usd / self.clicks if self.clicks else 0.0

    @property
    def cpa(self) -> float | None:
        """Cost per acquisition; None when there are no purchases yet."""
        return self.spend_usd / self.purchases if self.purchases else None

    @property
    def mer(self) -> float:
        """Marketing Efficiency Ratio = revenue / spend."""
        return self.revenue_usd / self.spend_usd if self.spend_usd else 0.0

    @property
    def atc_rate(self) -> float:
        return self.add_to_carts / self.clicks if self.clicks else 0.0

    def snapshot(self) -> dict:
        return {
            "spend_usd": round(self.spend_usd, 2), "impressions": self.impressions,
            "clicks": self.clicks, "add_to_carts": self.add_to_carts,
            "purchases": self.purchases, "revenue_usd": round(self.revenue_usd, 2),
            "ctr": round(self.ctr, 4), "cpc": round(self.cpc, 2),
            "cpa": round(self.cpa, 2) if self.cpa is not None else None,
            "mer": round(self.mer, 2), "atc_rate": round(self.atc_rate, 4),
        }


def aggregate_all(session, entity_type: str = "creative") -> list[EntityMetrics]:
    """Sum daily rows into one EntityMetrics per entity_id of the given type."""
    rows = session.execute(
        select(
            MetricsDaily.entity_id,
            func.sum(MetricsDaily.spend_usd), func.sum(MetricsDaily.impressions),
            func.sum(MetricsDaily.clicks), func.sum(MetricsDaily.add_to_carts),
            func.sum(MetricsDaily.purchases), func.sum(MetricsDaily.revenue_usd),
        )
        .where(MetricsDaily.entity_type == entity_type)
        .group_by(MetricsDaily.entity_id)
    ).all()
    return [
        EntityMetrics(entity_type=entity_type, entity_id=eid, spend_usd=float(sp or 0),
                      impressions=int(im or 0), clicks=int(cl or 0),
                      add_to_carts=int(atc or 0), purchases=int(pu or 0),
                      revenue_usd=float(rev or 0))
        for (eid, sp, im, cl, atc, pu, rev) in rows
    ]
