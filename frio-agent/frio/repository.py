"""Persistence helpers for Phase 1 research output."""

from __future__ import annotations

from .db.base import init_db, make_session_factory
from .db.models import Competitor, CompetitorAd, Decision, MetricsDaily, Product


def persist_research(
    database_url: str,
    seed: str,
    competitors: list[dict],
    ads: list[dict],
    plan: dict,
) -> dict:
    """Save discovered competitors, their ads+teardowns, and an audit Decision."""
    init_db(database_url)  # idempotent create_all
    Session = make_session_factory(database_url)
    with Session() as s:
        by_name: dict[str, Competitor] = {}
        for c in competitors:
            comp = Competitor(
                name=c["name"], relation=c["relation"],
                similarity_score=c["similarity_score"], website=c.get("website"),
                tiktok_handle=c.get("tiktok_handle"), seed_brand=seed,
                signals=c.get("signals", {}),
            )
            s.add(comp)
            by_name[c["name"].strip().lower()] = comp

        for item in ads:
            ad, teardown = item["ad"], item["teardown"]
            comp = by_name.get(ad["advertiser"].strip().lower())
            s.add(CompetitorAd(
                competitor=comp, source=ad["source"], external_id=ad.get("external_id"),
                media_url=ad.get("media_url"), raw={"text": ad.get("text")},
                teardown=teardown,
            ))

        s.add(Decision(
            kind="research", actor="engine", target=seed,
            rationale="Phase 1 competitor research + strategist plan",
            payload={"competitors": len(competitors), "ads": len(ads),
                     "plan_engine": plan.get("_engine")},
        ))
        s.commit()
    return {"competitors": len(competitors), "ads": len(ads)}


def persist_products(database_url: str, niche: str, candidates: list[dict],
                     threshold: float) -> dict:
    """Save POD/Dropship product candidates and an audit Decision."""
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        for c in candidates:
            meta = c.get("metadata", {})
            score = (meta.get("demand") or {}).get("score", 0.0)
            s.add(Product(
                kind=c["kind"], title=c["title"], source=c["source"],
                external_id=c.get("external_id"),
                demand_validated=score >= threshold, compliant=c.get("compliant", True),
                metadata_=meta,
            ))
        s.add(Decision(
            kind="product_select", actor="engine", target=niche,
            rationale="Phase 2 product origin (demand-validated)",
            payload={"count": len(candidates), "threshold": threshold},
        ))
        s.commit()
    return {"products": len(candidates)}


# Synthetic ad metrics for demoing/testing the optimize engine without live ads.
DEMO_METRICS = [
    # (entity_id, spend, impressions, clicks, atc, purchases, revenue)
    ("creative_A", 25.0, 5000, 10, 0, 0, 0.0),    # kill: $25 spent, 0 ATC
    ("creative_B", 30.0, 2000, 8, 1, 0, 0.0),     # kill: CTR 0.4% < 1%
    ("creative_C", 50.0, 4000, 120, 30, 15, 300.0),  # scale: MER 6 on 15 purchases
    ("creative_D", 10.0, 800, 12, 2, 0, 0.0),     # hold: insufficient data
]


def seed_metrics(database_url: str, rows=None) -> int:
    """Insert synthetic metrics_daily rows (demo/dev only)."""
    init_db(database_url)
    rows = rows if rows is not None else DEMO_METRICS
    Session = make_session_factory(database_url)
    with Session() as s:
        for eid, sp, im, cl, atc, pu, rev in rows:
            s.add(MetricsDaily(entity_type="creative", entity_id=eid, spend_usd=sp,
                               impressions=im, clicks=cl, add_to_carts=atc,
                               purchases=pu, revenue_usd=rev))
        s.commit()
    return len(rows)
