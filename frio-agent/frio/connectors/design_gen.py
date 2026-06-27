"""AI design generation — prompt -> design image.

Live: OpenAI Images (DALL·E) / Ideogram / Midjourney via API key. Offline:
returns a deterministic placeholder asset so the pipeline runs. Real image
generation has per-image cost — route through the spend ledger when wired.
"""

from __future__ import annotations

import hashlib

from ..config import Config
from .base import DesignAsset


class AIDesignGenerator:
    name = "dalle"

    def __init__(self, config: Config) -> None:
        self._config = config
        # Reuse the anthropic key field only as a presence example; real impl needs
        # an OpenAI/Ideogram key field added to Config.
        self._enabled = False  # offline until an image-gen key is configured

    def available(self) -> bool:
        return self._enabled

    def generate(self, prompt: str) -> DesignAsset:
        if not self.available():
            slug = hashlib.sha1(prompt.encode()).hexdigest()[:10]
            return DesignAsset(
                prompt=prompt, uri=f"placeholder://design/{slug}.png",
                provider=self.name, meta={"offline": True},
            )
        raise NotImplementedError("wire DALL·E/Ideogram image generation here")
