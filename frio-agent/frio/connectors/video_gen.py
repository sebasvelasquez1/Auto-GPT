"""AI-UGC video generation — prompt -> ~30s MP4.

Represents the glued providers (ad-factory-agent's Sora 2 / Veo 3.1, Prizmad,
Arcads) behind one switch. Offline returns a placeholder asset at $0 (no real
money), while ``list_price`` is the informational per-clip estimate shown in a
preview so the user sees what a live render would cost before approving.
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
    """Stand-in for Sora/Veo/Prizmad until a live provider key is wired."""

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
        # Live impl (Phase 3+): call Sora/Veo/Prizmad behind connectors.http.
        raise NotImplementedError("wire Sora/Veo/Prizmad video generation here")
