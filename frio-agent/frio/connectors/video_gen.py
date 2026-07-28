"""AI-UGC video generation — prompt -> ~30s MP4.

Provider-agnostic by design: a single switch behind which any text-to-video model
plugs in. We deliberately do NOT hard-depend on one vendor — OpenAI's Sora was
discontinued (consumer app off Apr 2026; API sunsets Sep 24 2026), which is
exactly the lock-in we avoid.

Default plan: Google **Veo 3.1** (best all-round + native audio + ad-friendly),
accessed via **fal.ai** (one API key -> 600+ models incl. Veo / Kling / Runway),
so swapping models is a config change, not an architecture change. Avatar-UGC
style stays available via Prizmad / Arcads.

Offline returns a placeholder asset at $0 (no real money); ``list_price`` is the
informational per-clip estimate shown in a preview before the user approves.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..config import Config


@dataclass
class VideoGenResult:
    uri: str | None
    cost_usd: float
    provider: str
    meta: dict = field(default_factory=dict)


class PlaceholderVideoGenerator:
    """Stand-in for the live providers (Veo/Kling/Runway via fal.ai, or
    Prizmad/Arcads) until a provider key is wired."""

    name = "placeholder"
    list_price = 0.50  # informational per-clip estimate for previews

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return False  # live video providers not wired yet

    def estimate(self) -> float:
        return self.list_price

    def generate(self, prompt: str) -> VideoGenResult:
        if not self.available():
            slug = hashlib.sha1(prompt.encode()).hexdigest()[:10]
            return VideoGenResult(
                uri=f"placeholder://video/{slug}.mp4", cost_usd=0.0,
                provider=self.name,
                meta={"offline": True, "would_cost_usd": self.list_price},
            )
        # Live impl (Phase 3+): call Veo 3.1 via fal.ai (or Prizmad/Arcads) behind
        # connectors.http; route the per-clip cost through the spend ledger.
        raise NotImplementedError("wire Veo-via-fal.ai (or Prizmad/Arcads) generation here")
