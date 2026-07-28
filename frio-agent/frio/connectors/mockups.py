"""Mockup generation — design -> product mockup.

Live: Printful API (`config.printful_api_key`) or dynamicmockups / automated_mockups.
Offline: deterministic placeholder mockup URI.
"""

from __future__ import annotations

import hashlib

from ..config import Config
from .base import DesignAsset, MockupAsset


class PrintfulMockupGenerator:
    name = "printful"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.printful_api_key)

    def render(self, design: DesignAsset, blank: str = "tee") -> MockupAsset:
        if not self.available():
            key = f"{design.uri}|{blank}"
            slug = hashlib.sha1(key.encode()).hexdigest()[:10]
            return MockupAsset(
                design_uri=design.uri, uri=f"placeholder://mockup/{blank}/{slug}.png",
                blank=blank, provider=self.name, meta={"offline": True},
            )
        # Live impl (Phase 2+): Printful mockup-generator task (printful-mcp pattern).
        raise NotImplementedError("wire Printful mockup generation here")
