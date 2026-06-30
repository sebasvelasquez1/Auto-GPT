"""Phase 2B — POD product origin (ungated).

The product is the SELLER'S OWN design (pulled from their TikTok Shop catalog) —
not generated, not a competitor's. Competitor/market analysis is used to decide
*what to print the designs on* (the blank/format — e.g. tank top vs tee), per the
seller's insight that competitor best-sellers reveal the winning format.

Flow: pull existing designs → recommend formats from competitor signal → pair each
design with the top format + a mockup → rank by theme demand → test matrix.

A second, FUTURE origin (`GeneratedDesignOrigin`) generates NEW designs informed by
market themes — deferred and guard-railed (IP + printability); see NOTES.md.
"""

from __future__ import annotations

from dataclasses import asdict

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.base import DemandProvider, DesignAsset, MockupGenerator
from ..connectors.demand import ErankProvider
from ..connectors.fixtures import offline_format_demand
from ..connectors.mockups import PrintfulMockupGenerator
from ..connectors.tiktok_shop_catalog import TikTokShopCatalog
from ..interfaces import ProductCandidate, ProductOrigin


def recommend_blanks(niche: str, top: int = 3) -> list[dict]:
    """Rank product formats (blanks) by competitor best-seller signal for the niche."""
    ranked = sorted(offline_format_demand(niche), key=lambda x: x[1], reverse=True)
    return [{"blank": b, "score": round(s, 2)} for b, s in ranked][:top]


class PODProductOrigin(ProductOrigin):
    kind = "pod"

    def __init__(self, config: Config, catalog=None,
                 demand: DemandProvider | None = None,
                 mockups: MockupGenerator | None = None) -> None:
        self._config = config
        self._catalog = catalog or TikTokShopCatalog(config)
        self._demand = demand or ErankProvider(config)
        self._mockups = mockups or PrintfulMockupGenerator(config)

    def discover(self, niche: str, limit: int = 20) -> list[ProductCandidate]:
        designs = self._catalog.list_designs()
        blanks = recommend_blanks(niche)              # competitor-informed formats
        top_blank = blanks[0]["blank"] if blanks else self._config.pod_blank
        rec_blank_names = [b["blank"] for b in blanks]

        out: list[ProductCandidate] = []
        for d in designs:
            s = self._demand.validate(d["theme"])     # is this theme in demand?
            design = DesignAsset(prompt=d["title"], uri=d["image_uri"],
                                 provider="existing-catalog")
            mockup = self._mockups.render(design, blank=top_blank)
            out.append(ProductCandidate(
                external_id=d["design_id"], title=d["title"], source="existing-catalog",
                kind=self.kind, compliant=True,
                metadata={
                    "design_id": d["design_id"], "design_uri": d["image_uri"],
                    "theme": d["theme"], "blank": top_blank,
                    "recommended_blanks": rec_blank_names, "mockup_uri": mockup.uri,
                    "demand": {"search_volume": s.search_volume, "competition": s.competition,
                               "score": s.score, "source": s.source},
                    "offline": bool(d.get("offline")),
                },
            ))
        # We test all OUR designs, ranked by theme demand (highest first).
        out.sort(key=lambda c: c.metadata["demand"]["score"], reverse=True)
        return out[:limit]


def scale_winner_to_formats(design_id: str, niche: str, config: Config | None = None, *,
                            top: int = 3, catalog=None, demand: DemandProvider | None = None,
                            mockups=None) -> list[ProductCandidate]:
    """Phase 2: take a WINNING design and scale it onto more competitor-top formats.

    Your own proven design × the top recommended blanks (tank/muscle/tee/…). No IP
    risk (it's your design); just multiply what already works onto more products.
    """
    if top <= 0:
        raise ValueError(f"top must be >= 1, got {top}")
    config = config or load_config()
    catalog = catalog or TikTokShopCatalog(config)
    demand = demand or ErankProvider(config)
    mockups = mockups or PrintfulMockupGenerator(config)

    design = next((d for d in catalog.list_designs() if d["design_id"] == design_id), None)
    if design is None:
        return []

    # Scaled winners inherit their theme's demand validation (same design).
    s = demand.validate(design["theme"])
    out: list[ProductCandidate] = []
    for b in recommend_blanks(niche, top=top):
        asset = DesignAsset(prompt=design["title"], uri=design["image_uri"],
                            provider="existing-catalog")
        mockup = mockups.render(asset, blank=b["blank"])
        out.append(ProductCandidate(
            external_id=design["design_id"], title=f"{design['title']} — {b['blank']}",
            source="scaled-winner", kind="pod", compliant=True,
            metadata={"design_id": design["design_id"], "design_uri": design["image_uri"],
                      "theme": design["theme"], "blank": b["blank"],
                      "format_score": b["score"], "scaled_from_winner": True,
                      "mockup_uri": mockup.uri,
                      "demand": {"search_volume": s.search_volume, "competition": s.competition,
                                 "score": s.score, "source": s.source}},
        ))
    return out


class GeneratedDesignOrigin(ProductOrigin):
    """FUTURE parallel workflow — generate NEW designs informed by market themes.

    DEFERRED & GUARD-RAILED (see NOTES.md). Before enabling:
      - IP: brief on ABSTRACTED winning themes/formats only — never copy competitor
        artwork; trademark/wordmark check on any text; originality/similarity review.
      - Printability: resolution/DPI/transparency/safe-area gate.
      - Human approval before any generated design is listed.
    Seed it with REAL winners from testing the existing catalog first.
    """

    kind = "pod"

    def discover(self, niche: str, limit: int = 20) -> list[ProductCandidate]:
        raise NotImplementedError(
            "future: market-informed AI design generation (guard-railed) — see NOTES.md.")


def make_product_origin(config: Config) -> ProductOrigin:
    """Select the active pipeline's product-origin implementation."""
    if config.pipeline == "pod":
        return PODProductOrigin(config)
    raise NotImplementedError(
        f"product origin for pipeline '{config.pipeline}' not built yet "
        "(Dropshipping origin lands in a later phase).")


@capability(
    "product.pod.discover",
    "Pair the seller's existing designs with competitor-recommended formats (blanks).",
    parameters={"niche": {"type": "string", "required": True},
                "limit": {"type": "integer", "required": False}},
    category="research",
)
def discover_pod(niche: str, limit: int = 20, config: Config | None = None) -> list[dict]:
    config = config or load_config()
    return [asdict(p) for p in PODProductOrigin(config).discover(niche, limit=limit)]


@capability(
    "product.pod.scale_winner",
    "Phase 2: scale a winning design onto more competitor-recommended formats.",
    parameters={"design_id": {"type": "string", "required": True},
                "niche": {"type": "string", "required": True}},
    category="research",
)
def scale_winner(design_id: str, niche: str, top: int = 3,
                 config: Config | None = None) -> list[dict]:
    config = config or load_config()
    return [asdict(p) for p in scale_winner_to_formats(design_id, niche, config, top=top)]
