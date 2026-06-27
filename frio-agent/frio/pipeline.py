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


@dataclass
class Phase2Result:
    niche: str
    pipeline: str
    products: list[dict]
    offline: bool
    persisted: dict = field(default_factory=dict)


def run_phase2(
    niche: str | None = None,
    *,
    limit: int = 20,
    config: Config | None = None,
    persist: bool = True,
) -> Phase2Result:
    """Phase 2 product origin (POD by default): demand-validate -> design -> mockup."""
    from dataclasses import asdict

    from .modules.product_pod import make_product_origin

    config = config or load_config()
    niche = niche or config.niche
    origin = make_product_origin(config)
    products = [asdict(p) for p in origin.discover(niche, limit=limit)]
    offline = any(p["metadata"].get("offline") for p in products) if products else True

    result = Phase2Result(niche=niche, pipeline=config.pipeline, products=products,
                          offline=offline)
    if persist:
        from . import repository

        result.persisted = repository.persist_products(
            config.database_url, niche, products, config.demand_threshold)
    return result


@dataclass
class Phase3Result:
    product: dict | None
    brief: dict | None
    estimated_cost_usd: float
    rendered: dict | None = None  # populated only when approved + gates pass
    gate_message: str | None = None  # why a render was blocked (if it was)


def run_phase3(
    niche: str | None = None,
    seed: str | None = None,
    *,
    approve: bool = False,
    config: Config | None = None,
    persist: bool = True,
) -> Phase3Result:
    """Phase 3: pick the top product + hook, build a UGC brief, optionally render.

    Without ``approve`` this is a no-spend preview. With ``approve`` it attempts a
    render, which still must pass the creation gate + spend caps.
    """
    from .modules import creation

    config = config or load_config()
    llm = make_llm(config)

    p1 = run_phase1(seed=seed, config=config, persist=False)
    p2 = run_phase2(niche=niche, config=config, persist=False)
    if not p2.products:
        return Phase3Result(product=None, brief=None, estimated_cost_usd=0.0,
                            gate_message="no demand-validated products")

    product = p2.products[0]
    hooks = p1.plan.get("hook_bank", [])
    prev = creation.preview(product, hooks, config, llm)
    result = Phase3Result(product=product, brief=prev["brief"],
                          estimated_cost_usd=prev["estimated_cost_usd"])

    if approve:
        try:
            result.rendered = creation.render_video(
                prev["brief"], config, approve=True,
                database_url=config.database_url if persist else "sqlite://")
        except (PermissionError, Exception) as exc:  # gate / cap blocks are expected
            from .spend import SpendCapError

            if isinstance(exc, (PermissionError, SpendCapError)):
                result.gate_message = str(exc)
            else:
                raise
    return result
