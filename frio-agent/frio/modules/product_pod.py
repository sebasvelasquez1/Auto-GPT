"""Phase 2B — POD product origin (ungated).

The POD discipline: validate demand BEFORE designing. For a niche, mine candidate
design keywords, validate search demand (eRank), keep those above threshold, then
generate a design + product mockup for each survivor.

Implements the ``ProductOrigin`` interface so the shared engine treats POD and
Dropshipping identically downstream.
"""

from __future__ import annotations

from dataclasses import asdict

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.base import DemandProvider, DesignGenerator, MockupGenerator
from ..connectors.demand import ErankProvider
from ..connectors.design_gen import AIDesignGenerator
from ..connectors.fixtures import offline_keyword_ideas
from ..connectors.mockups import PrintfulMockupGenerator
from ..interfaces import ProductCandidate, ProductOrigin


class PODProductOrigin(ProductOrigin):
    kind = "pod"

    def __init__(
        self,
        config: Config,
        demand: DemandProvider | None = None,
        designer: DesignGenerator | None = None,
        mockups: MockupGenerator | None = None,
    ) -> None:
        self._config = config
        self._demand = demand or ErankProvider(config)
        self._designer = designer or AIDesignGenerator(config)
        self._mockups = mockups or PrintfulMockupGenerator(config)

    def candidate_keywords(self, niche: str) -> list[str]:
        # Production: merge Phase-1 winning angles + eRank keyword mining.
        return offline_keyword_ideas(niche)

    def discover(self, niche: str, limit: int = 20) -> list[ProductCandidate]:
        threshold = self._config.demand_threshold
        blank = self._config.pod_blank

        signals = [self._demand.validate(kw) for kw in self.candidate_keywords(niche)]
        passing = sorted(
            (s for s in signals if s.score >= threshold),
            key=lambda s: s.score, reverse=True,
        )[:limit]

        out: list[ProductCandidate] = []
        for s in passing:
            prompt = f"{s.keyword}, spirituality/wellbeing aesthetic, print-ready design"
            design = self._designer.generate(prompt)
            mockup = self._mockups.render(design, blank=blank)
            out.append(ProductCandidate(
                external_id=None, title=s.keyword, source="ai-design", kind=self.kind,
                compliant=True,  # POD products are inherently compliant (you create them)
                metadata={
                    "keyword": s.keyword,
                    "demand": {"search_volume": s.search_volume,
                               "competition": s.competition, "score": s.score,
                               "source": s.source},
                    "design_uri": design.uri, "design_provider": design.provider,
                    "mockup_uri": mockup.uri, "blank": mockup.blank,
                    "offline": bool(s.meta.get("offline")),
                },
            ))
        return out


def make_product_origin(config: Config) -> ProductOrigin:
    """Select the active pipeline's product-origin implementation."""
    if config.pipeline == "pod":
        return PODProductOrigin(config)
    raise NotImplementedError(
        f"product origin for pipeline '{config.pipeline}' not built yet "
        "(Dropshipping origin lands in a later phase)."
    )


@capability(
    "product.pod.discover",
    "Validate POD design demand, then generate design + mockup for survivors.",
    parameters={
        "niche": {"type": "string", "required": True},
        "limit": {"type": "integer", "required": False},
    },
    category="research",
)
def discover_pod(niche: str, limit: int = 20, config: Config | None = None) -> list[dict]:
    config = config or load_config()
    origin = PODProductOrigin(config)
    return [asdict(p) for p in origin.discover(niche, limit=limit)]
