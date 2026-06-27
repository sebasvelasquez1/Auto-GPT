"""Phase 1 pipeline: discover -> research ads -> teardown -> 30-day plan.

Plain composable functions (Prefect flow wrappers come when we need scheduling).
Runs fully offline when keys are absent; flags ``offline`` so callers can warn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .config import Config, load_config
from .connectors.ad_sources import CreativeCenterSource, MetaAdLibrarySource
from .connectors.base import AdSource, RawAd
from .llm.client import make_llm
from .modules import competitors as competitors_mod
from .modules import strategist


@dataclass
class Phase1Result:
    seed: str
    competitors: list[dict]
    ads: list[dict]  # [{"ad": {...}, "teardown": {...}}, ...]
    plan: dict
    offline: bool
    persisted: dict = field(default_factory=dict)


def _fetch_ads(sources: list[AdSource], advertiser: str, limit: int) -> list[RawAd]:
    """Use the first source that returns ads (avoids duplicate offline fixtures)."""
    for src in sources:
        ads = src.fetch_ads(advertiser, limit=limit)
        if ads:
            return ads
    return []


def run_phase1(
    seed: str | None = None,
    *,
    limit_competitors: int = 5,
    ads_per_competitor: int = 5,
    config: Config | None = None,
    persist: bool = True,
) -> Phase1Result:
    config = config or load_config()
    seed = seed or config.seed_brands
    llm = make_llm(config)

    competitors = competitors_mod.discover(seed, limit=limit_competitors, config=config)

    sources: list[AdSource] = [CreativeCenterSource(config), MetaAdLibrarySource(config)]
    ads: list[dict] = []
    for c in competitors:
        for raw in _fetch_ads(sources, c["name"], ads_per_competitor):
            ads.append({"ad": asdict(raw), "teardown": strategist.teardown_ad(raw, llm)})

    teardowns = [a["teardown"] for a in ads]
    plan = strategist.build_30_day_plan(seed, competitors, teardowns, llm)
    offline = plan["_engine"] == "heuristic"

    result = Phase1Result(seed=seed, competitors=competitors, ads=ads, plan=plan, offline=offline)
    if persist:
        from . import repository

        result.persisted = repository.persist_research(
            config.database_url, seed, competitors, ads, plan)
    return result
