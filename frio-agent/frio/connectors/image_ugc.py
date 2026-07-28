"""UGC image generation — prompt -> still image (for carousel ad slides).

Provider-agnostic, same as video. Default plan: Higgsfield's **Nano Banana Pro**
(top photorealism + character consistency) / **Soul 2.0** (editorial hero shots),
reached via Higgsfield's official MCP server (one integration -> 30+ models),
with Flux 2 / GPT Image 2 as alternatives. Cheap (~$0.01-0.12/image).

Offline returns a $0 placeholder; ``list_price`` is the informational per-image
estimate shown before approval.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..config import Config


@dataclass
class ImageGenResult:
    uri: str | None
    cost_usd: float
    provider: str
    meta: dict = field(default_factory=dict)


class HiggsfieldImageGenerator:
    """Stand-in for Nano Banana Pro / Soul 2.0 (via Higgsfield MCP) until wired."""

    name = "nano_banana"
    list_price = 0.10  # informational per-image estimate

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.higgsfield_api_key)

    def estimate(self) -> float:
        return self.list_price

    def generate(self, prompt: str) -> ImageGenResult:
        if not self.available():
            slug = hashlib.sha1(prompt.encode()).hexdigest()[:10]
            return ImageGenResult(
                uri=f"placeholder://image/{slug}.png", cost_usd=0.0,
                provider=self.name,
                meta={"offline": True, "would_cost_usd": self.list_price},
            )
        # Live impl: call Higgsfield (Nano Banana Pro/Soul) via its MCP/API behind
        # connectors.http; route each image's cost through the spend ledger.
        raise NotImplementedError("wire Higgsfield image generation (Nano Banana/Soul) here")
