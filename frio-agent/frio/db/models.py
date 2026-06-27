"""Core schema. Postgres in prod (JSON -> JSONB); SQLite for tests.

`decisions` and `spend_ledger` are the sacred audit trail: every automated
action and every human approval is appended there.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Competitor(Base):
    """A competitor discovered to share OUR customers (Phase 1a).

    Discovery seeds from a reference brand (e.g. "Spiritual Gangster") and
    expands by audience overlap; ranked by client similarity.
    """

    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tiktok_handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seed_brand: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # direct | indirect | aspirational
    relation: Mapped[str] = mapped_column(String(32), default="direct")
    # 0..1 — audience-overlap / client-similarity score
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    ads: Mapped[list["CompetitorAd"]] = relationship(back_populates="competitor")


class CompetitorAd(Base):
    """A competitor ad + its strategist teardown (hook/pattern-interrupt/payoff)."""

    __tablename__ = "competitor_ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int | None] = mapped_column(ForeignKey("competitors.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(64))  # creative_center | meta_ad_lib | apify
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    teardown: Mapped[dict] = mapped_column(JSON, default=dict)  # JSONB on Postgres
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    competitor: Mapped["Competitor"] = relationship(back_populates="ads")


class Product(Base):
    """A testable product. kind = dropship (sourced) | pod (designed)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # dropship | pod
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    demand_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    compliant: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CreativeBrief(Base):
    __tablename__ = "creative_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    angle: Mapped[str | None] = mapped_column(String(256), nullable=True)
    funnel_stage: Mapped[str] = mapped_column(String(32), default="cold")  # cold|warm|retargeting
    brief: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brief_id: Mapped[int | None] = mapped_column(ForeignKey("creative_briefs.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64))  # sora|veo|prizmad|arcads
    uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)  # HITL render gate
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MetricsDaily(Base):
    """Daily ad/sales metrics feeding the optimize engine."""

    __tablename__ = "metrics_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # campaign|ad_set|creative
    entity_id: Mapped[str] = mapped_column(String(128))
    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    spend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    add_to_carts: Mapped[int] = mapped_column(Integer, default=0)
    purchases: Mapped[int] = mapped_column(Integer, default=0)
    revenue_usd: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[float] = mapped_column(Float, default=0.0)


class Decision(Base):
    """Audit log: every automated action + human approval. Append-only."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))  # kill|scale|launch|publish|render|approve
    actor: Mapped[str] = mapped_column(String(32), default="engine")  # engine|human
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SpendLedger(Base):
    """Every dollar committed. Spend caps are enforced against this. Append-only."""

    __tablename__ = "spend_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32))  # ads|creation
    amount_usd: Mapped[float] = mapped_column(Float)
    reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
