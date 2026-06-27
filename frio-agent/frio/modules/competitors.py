"""Phase 1a — Competitor Discovery (ungated).

Find *which* competitors share OUR customers, then feed the most-similar ones to
ad research. Seeds from a reference brand (default "Spiritual Gangster") and
expands by audience overlap across providers (Similarweb web-traffic overlap +
SparkToro social overlap), then ranks by client similarity and tags each
direct / indirect / aspirational.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.base import AudienceOverlap, DiscoveryProvider
from ..connectors.similarweb import SimilarwebProvider
from ..connectors.sparktoro import SparkToroProvider

# Large/established brands treated as aspirational competitors.
_ASPIRATIONAL = {"alo yoga", "gaiam", "lululemon"}


@dataclass
class DiscoveredCompetitor:
    name: str
    relation: str  # direct | indirect | aspirational
    similarity_score: float  # 0..1
    website: str | None = None
    tiktok_handle: str | None = None
    signals: dict = field(default_factory=dict)


def _build_providers(config: Config) -> list[DiscoveryProvider]:
    return [SimilarwebProvider(config), SparkToroProvider(config)]


def _score(overlaps: list[AudienceOverlap]) -> list[DiscoveredCompetitor]:
    """Merge per-provider overlaps into one ranked, tagged competitor list."""
    grouped: dict[str, list[AudienceOverlap]] = {}
    for o in overlaps:
        grouped.setdefault(o.name.strip().lower(), []).append(o)

    out: list[DiscoveredCompetitor] = []
    for key, items in grouped.items():
        sources = {i.source for i in items}
        sim = sum(i.overlap for i in items) / len(items)
        if len(sources) > 1:  # corroborated across web + social = stronger signal
            sim = min(1.0, sim + 0.1)
        if key in _ASPIRATIONAL:
            relation = "aspirational"
        elif len(sources) > 1:
            relation = "direct"
        elif sim >= 0.6:
            relation = "indirect"
        else:
            relation = "aspirational"
        website = next((i.website for i in items if i.website), None)
        handle = next((i.tiktok_handle for i in items if i.tiktok_handle), None)
        out.append(DiscoveredCompetitor(
            name=items[0].name, relation=relation, similarity_score=round(sim, 2),
            website=website, tiktok_handle=handle,
            signals={"sources": sorted(sources), "offline": all(
                i.meta.get("offline") for i in items)},
        ))
    return sorted(out, key=lambda c: c.similarity_score, reverse=True)


@capability(
    "competitors.discover",
    "Discover competitors who share our customers, ranked by client similarity.",
    parameters={
        "seed": {"type": "string", "description": "Seed brand name", "required": True},
        "limit": {"type": "integer", "description": "Max competitors", "required": False},
    },
    category="research",
)
def discover(
    seed: str,
    limit: int = 20,
    config: Config | None = None,
    providers: list[DiscoveryProvider] | None = None,
) -> list[dict]:
    """Return ranked competitors whose audience overlaps the seed brand's."""
    config = config or load_config()
    providers = providers if providers is not None else _build_providers(config)

    overlaps: list[AudienceOverlap] = []
    for p in providers:
        overlaps.extend(p.overlaps(seed, limit=limit))

    ranked = _score(overlaps)
    # The seed brand itself is the canonical direct competitor at full similarity.
    seed_row = DiscoveredCompetitor(
        name=seed, relation="direct", similarity_score=1.0, signals={"seed": True})
    ranked = [seed_row] + [c for c in ranked if c.name.strip().lower() != seed.strip().lower()]
    return [asdict(c) for c in ranked[:limit]]
