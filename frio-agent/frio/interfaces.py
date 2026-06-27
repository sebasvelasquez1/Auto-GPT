"""Swappable pipeline interfaces.

The shared engine is built once; the two business models (POD, Dropshipping)
each implement ``ProductOrigin`` (where the product comes from) and
``Fulfillment`` (how an order is produced/shipped). Everything else — competitor
discovery, ad research, strategist, creation, optimize, ads — is common.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductCandidate:
    """A product the pipeline could test.

    For Dropshipping this is a sourced SKU (+ supplier); for POD it is a created
    design (+ blank/provider).
    """

    external_id: str
    title: str
    source: str  # e.g. "cj", "zendrop", "printful", "ai-design"
    kind: str  # "dropship" | "pod"
    metadata: dict[str, Any] = field(default_factory=dict)
    compliant: bool = True  # dropship: must use TikTok-Shop-approved supplier


@dataclass
class FulfillmentResult:
    external_order_id: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


class ProductOrigin(ABC):
    """Where a testable product comes from."""

    kind: str  # "dropship" | "pod"

    @abstractmethod
    def discover(self, niche: str, limit: int = 20) -> list[ProductCandidate]:
        """Return validated/candidate products for the niche."""


class Fulfillment(ABC):
    """How a product is published and orders are produced/shipped. GATED."""

    @abstractmethod
    def publish_product(self, product: ProductCandidate) -> str:
        """Create the listing (returns external product/listing id). HITL gated."""

    @abstractmethod
    def create_order(self, listing_id: str, address: dict[str, Any]) -> FulfillmentResult:
        """Produce/ship one order. HITL gated."""
