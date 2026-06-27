"""Phase 1a — Competitor Discovery (ungated).

Find *which* competitors share OUR customers, then feed the most-similar ones to
ad research. Seeds from a reference brand (default: "Spiritual Gangster") and
expands by audience overlap (Similarweb/SparkToro), TikTok shop/creator DBs
(FastMoss/Kalodata) and social listening; ranks by client-similarity.

Phase 0 ships the capability surface + a deterministic stub so the pipeline
wires end-to-end; real connectors land in Phase 1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..capabilities import capability


@dataclass
class DiscoveredCompetitor:
    name: str
    relation: str  # direct | indirect | aspirational
    similarity_score: float  # 0..1 audience overlap / client similarity
    website: str | None = None
    tiktok_handle: str | None = None
    signals: dict = field(default_factory=dict)


# Deterministic placeholder until Similarweb/SparkToro/FastMoss connectors land.
_STUB_EXPANSION: dict[str, list[DiscoveredCompetitor]] = {
    "spiritual gangster": [
        DiscoveredCompetitor("Spiritual Gangster", "direct", 1.0, "spiritualgangster.com",
                             signals={"seed": True}),
        DiscoveredCompetitor("Wanderlust", "indirect", 0.71, "wanderlust.com"),
        DiscoveredCompetitor("Alo Yoga", "aspirational", 0.64, "aloyoga.com"),
        DiscoveredCompetitor("Manifestation Co", "direct", 0.58),
    ]
}


@capability(
    "competitors.discover",
    "Discover competitors who share our customers, ranked by client similarity.",
    parameters={
        "seed": {"type": "string", "description": "Seed brand name", "required": True},
        "limit": {"type": "integer", "description": "Max competitors", "required": False},
    },
    category="research",
)
def discover(seed: str, limit: int = 20) -> list[dict]:
    """Return ranked competitors whose audience overlaps the seed brand's."""
    found = _STUB_EXPANSION.get(seed.strip().lower(), [
        DiscoveredCompetitor(seed, "direct", 1.0, signals={"seed": True})
    ])
    ranked = sorted(found, key=lambda c: c.similarity_score, reverse=True)[:limit]
    return [asdict(c) for c in ranked]
