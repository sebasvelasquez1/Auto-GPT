"""TikTok Shop product catalog — pull the seller's EXISTING designs.

In POD, the product is the seller's own design (already in their TikTok Shop;
Shopify later). This is the real product source — NOT generated, NOT a competitor's.
Live: TikTok Shop API (`tiktok_shop_api_key`). Offline: fixtures of designs the
seller "already owns".
"""

from __future__ import annotations

from ..config import Config
from .fixtures import offline_existing_designs


class TikTokShopCatalog:
    name = "tiktok_shop"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.tiktok_shop_api_key)

    def list_designs(self, limit: int = 50) -> list[dict]:
        """Return the seller's existing designs: {design_id, title, theme, image_uri}."""
        if not self.available():
            return [dict(d, offline=True) for d in offline_existing_designs()][:limit]
        # Live: pull the product catalog (EcomPHP/Lundehund tiktok-shop SDK).
        raise NotImplementedError("wire TikTok Shop product-catalog pull here")
