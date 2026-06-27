"""Persistence helpers for Phase 1 research output."""

from __future__ import annotations

from .db.base import init_db, make_session_factory
from .db.models import Competitor, CompetitorAd, Decision


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
