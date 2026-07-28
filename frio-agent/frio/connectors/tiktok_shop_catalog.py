"""TikTok Shop product catalog — pull the seller's EXISTING designs.

In POD, the product is the seller's own design (already in their TikTok Shop;
Shopify later). This is the real product source — NOT generated, NOT a competitor's.

REAL API contract (verified from the official TikTok Shop developer guide, not
guessed):
  - We are a "Seller (in-house) developer" -> Custom app -> user_type=0, own shop
    data only.
  - Host: https://open-api.tiktokglobalshop.com
  - Every request is SIGNED and carries: query params app_key, sign, timestamp;
    headers x-tts-access-token + content-type: application/json.
  - NO Python client exists anywhere (verified: not on PyPI, no repo with tests, no
    packaged project). We call the REST API directly. (An earlier note here named
    Lundehund/tiktok-shop-api as a candidate — REMOVED: that repo now 404s and was a
    RapidAPI scraper proxy, not the Partner API.) Reference layouts worth reading:
    EcomPHP/tiktokshop-php (Apache-2.0, 18 modules) and hsib19/tiktok-shop-sdk (MIT).

SIGNING: ✅ SOLVED — see ``tiktok_sign.py``. The algorithm was verified by locally
reproducing two independent published test vectors (TikTok's own doc example and the
EcomPHP SDK unit test), pinned in tests/test_tiktok_sign.py. Not guessed.

STILL NEEDED before the live call can be written (honest gaps — not invented):
  1. The exact Products API list endpoint/path + params (Products API overview).
  2. Real credentials (app_key/app_secret/access_token) after app review.
  3. Confirmation of WHICH Partner Center onboarding path a seller-developer takes
     (the "Start Business" business-certificate flow appears to be the service-partner
     funnel, not ours — its region choice is IRREVERSIBLE, so do not submit blind).

Offline: fixtures of designs the seller "already owns".
"""

from __future__ import annotations

from ..config import Config
from .fixtures import offline_existing_designs

API_HOST = "https://open-api.tiktokglobalshop.com"


class TikTokShopCatalog:
    name = "tiktok_shop"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        # A signed live call needs the app credentials AND a per-shop access token.
        return bool(self._config.tiktok_shop_app_key
                    and self._config.tiktok_shop_app_secret
                    and self._config.tiktok_shop_access_token)

    def list_designs(self, limit: int = 50) -> list[dict]:
        """Return the seller's existing designs: {design_id, title, theme, image_uri}."""
        if not self.available():
            return [dict(d, offline=True) for d in offline_existing_designs()][:limit]
        # Live (needs items 1-2 above): GET Products API on API_HOST, signed with
        # app_key/app_secret/timestamp, header x-tts-access-token; map each product
        # -> {design_id, title, theme, image_uri}.
        raise NotImplementedError(
            "TikTok Shop live catalog pull: signature algorithm + Products endpoint "
            "still required (see module docstring).")
