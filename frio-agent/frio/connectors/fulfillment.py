"""Fulfillment backends — publish listings + produce/ship orders.

Two pipelines behind the shared ``Fulfillment`` interface:
  - POD       -> Printful (create product, mockups, auto-fulfill on order)
  - Dropship  -> CJ Dropshipping (auto-buy from an approved supplier, ship)

Both are GATED (require an approved seller) and offline-safe (placeholder ids
when no key). The deterministic gate + human approval live one layer up in
``modules/commerce.py``; these connectors just do the I/O.
"""

from __future__ import annotations

import hashlib

from ..config import Config
from ..interfaces import Fulfillment, FulfillmentResult, ProductCandidate


def _slug(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:10]


class PrintfulFulfillment(Fulfillment):
    name = "printful"
    kind = "pod"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.printful_api_key)

    def unit_cost_for(self, blank: str) -> dict | None:
        """What one unit of ``blank`` costs the seller: {product_cost, shipping_cost}.

        Part of the autonomy path — the agent derives a product's cost from the
        fulfilment provider instead of asking a human to type it. Returns None when
        this provider cannot say, so the caller can fall back rather than assume zero.

        Live: Printful's v2 catalog exposes per-variant prices (base price by technique,
        placement costs, quantity discounts) at api.printful.com/v2 — see
        developers.printful.com/docs/v2-beta. The exact response mapping is NOT wired
        yet and is deliberately not guessed here; offline figures are used until it is.
        """
        from .fixtures import offline_blank_cost

        return offline_blank_cost(blank)

    def publish_product(self, product: ProductCandidate) -> str:
        if not self.available():
            return f"printful-offline-{_slug(product.title)}"
        # Live: Printful create-product (sync product + variants + print files).
        raise NotImplementedError("wire Printful product creation here")

    def create_order(self, listing_id: str, address: dict) -> FulfillmentResult:
        if not self.available():
            return FulfillmentResult(external_order_id=f"po-offline-{_slug(listing_id)}",
                                     status="submitted_offline", detail={"offline": True})
        raise NotImplementedError("wire Printful order submission here")


class CJFulfillment(Fulfillment):
    name = "cj"
    kind = "dropship"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.cj_api_key)

    def publish_product(self, product: ProductCandidate) -> str:
        # Compliance: dropshipping must use a TikTok-Shop-approved supplier
        # (no retail arbitrage). Refuse non-compliant products outright.
        if not product.compliant:
            raise PermissionError(
                "dropship product is non-compliant (retail-arbitrage); "
                "use a TikTok-Shop-approved supplier.")
        if not self.available():
            return f"cj-offline-{_slug(product.title)}"
        raise NotImplementedError("wire CJ Dropshipping product listing here")

    def create_order(self, listing_id: str, address: dict) -> FulfillmentResult:
        if not self.available():
            return FulfillmentResult(external_order_id=f"cj-offline-{_slug(listing_id)}",
                                     status="submitted_offline", detail={"offline": True})
        raise NotImplementedError("wire CJ Dropshipping order/auto-buy here")


def make_fulfillment(config: Config) -> Fulfillment:
    """Select the active pipeline's fulfillment backend."""
    if config.pipeline == "pod":
        return PrintfulFulfillment(config)
    if config.pipeline == "dropship":
        return CJFulfillment(config)
    raise NotImplementedError(f"no fulfillment backend for pipeline '{config.pipeline}'")
