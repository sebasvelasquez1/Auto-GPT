"""Derive each product's economics AUTOMATICALLY. Manual entry is the fallback.

This is an autonomous agent: it is supposed to read what is in the shop and work out
whether each product makes money, without a human typing numbers in. An earlier design
made a manual cost file the primary input, which was backwards — correct: the owner
called it out (2026-09-18).

Where each number legitimately comes from, in order:

  price          <- the TikTok Shop listing itself (the shop knows what it charges)
  product_cost   <- the fulfilment provider (Printful knows what a blank + print costs)
  shipping_cost  <- the fulfilment provider
  fees           <- config, from TikTok's published rates (see config.fin_platform_fee_pct)
  return_rate    <- config default until real order history supersedes it

Only what no connector can supply falls through to the manual file, and every figure
carries WHERE IT CAME FROM so a verdict can never quietly rest on a typed-in guess that
looks identical to live data.

Honest status: offline the whole path runs on fixtures shaped like the real responses.
Live, ``TikTokShopCatalog`` needs Shop API credentials and ``PrintfulFulfillment`` needs
a Printful key — neither is invented here. Once those exist this becomes automatic with
no change at the call sites, which is the point of resolving through connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .financials import CostStructure

# Where a number came from. Ordered most to least trustworthy.
FROM_SHOP = "shop_catalog"
FROM_FULFILLMENT = "fulfillment_provider"
FROM_MANUAL = "manual_entry"
FROM_CONFIG = "config_default"
AUTOMATIC_SOURCES = (FROM_SHOP, FROM_FULFILLMENT)


@dataclass
class ResolvedCost:
    sku: str
    price: float | None = None
    product_cost: float | None = None
    shipping_cost: float = 0.0
    affiliate_pct: float = 0.0
    return_rate: float | None = None
    sources: dict[str, str] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)

    def complete(self) -> bool:
        return not self.gaps

    def fully_automatic(self) -> bool:
        """True when no human typed any of the figures that drive the verdict."""
        return self.complete() and all(
            self.sources.get(k) in AUTOMATIC_SOURCES for k in ("price", "product_cost"))

    def snapshot(self) -> dict:
        return {"sku": self.sku, "price": self.price, "product_cost": self.product_cost,
                "shipping_cost": self.shipping_cost, "sources": dict(self.sources),
                "gaps": list(self.gaps), "automatic": self.fully_automatic()}

    def to_cost_structure(self, config: Config) -> CostStructure:
        if not self.complete():
            from .product_costs import MissingCostsError
            raise MissingCostsError(
                f"product {self.sku!r} is missing {' and '.join(self.gaps)} — no verdict "
                f"can be computed. Connect the source that supplies it "
                f"(shop catalog for price, fulfilment provider for cost), or set it "
                f"manually: frio costs set --sku {self.sku} ...")
        return CostStructure(
            price=self.price, product_cost=self.product_cost,
            fulfillment_cost=self.shipping_cost,
            platform_fee_pct=config.fin_platform_fee_pct,
            payment_fee_pct=config.fin_payment_fee_pct,
            affiliate_pct=self.affiliate_pct,
            return_rate=(config.fin_default_return_rate if self.return_rate is None
                         else self.return_rate))


def _manual(sku: str, manual_path: str):
    from .product_costs import load_costs

    return load_costs(manual_path).get(sku)


def resolve_cost(sku: str, config: Config, *, blank: str | None = None,
                 catalog=None, fulfillment=None,
                 manual_path: str = "product_costs.json") -> ResolvedCost:
    """Work out one product's economics from connectors first, manual file second."""
    from .connectors.fulfillment import make_fulfillment
    from .connectors.tiktok_shop_catalog import TikTokShopCatalog

    catalog = catalog if catalog is not None else TikTokShopCatalog(config)
    fulfillment = fulfillment if fulfillment is not None else make_fulfillment(config)
    manual = _manual(sku, manual_path)
    out = ResolvedCost(sku=sku)

    # price — the shop is authoritative about what it charges.
    price = catalog.price_for(sku) if hasattr(catalog, "price_for") else None
    if price:
        out.price, out.sources["price"] = float(price), FROM_SHOP
    elif manual.price:
        out.price, out.sources["price"] = float(manual.price), FROM_MANUAL
    else:
        out.gaps.append("price")

    # product_cost + shipping — the fulfilment provider is authoritative about cost.
    blank = blank or getattr(manual, "blank", None)
    quote = (fulfillment.unit_cost_for(blank)
             if blank and hasattr(fulfillment, "unit_cost_for") else None)
    if quote and quote.get("product_cost") is not None:
        out.product_cost = float(quote["product_cost"])
        out.sources["product_cost"] = FROM_FULFILLMENT
        out.shipping_cost = float(quote.get("shipping_cost") or 0.0)
        out.sources["shipping_cost"] = FROM_FULFILLMENT
    elif manual.product_cost is not None:
        out.product_cost = float(manual.product_cost)
        out.sources["product_cost"] = FROM_MANUAL
        out.shipping_cost = float(manual.shipping_cost or 0.0)
        out.sources["shipping_cost"] = FROM_MANUAL
    else:
        out.gaps.append("product_cost")

    out.affiliate_pct = float(manual.affiliate_pct or 0.0)
    out.return_rate = manual.return_rate
    out.sources.setdefault("fees", FROM_CONFIG)
    return out


def resolve_all(config: Config, *, catalog=None, fulfillment=None,
                manual_path: str = "product_costs.json") -> list[ResolvedCost]:
    """The autonomous path: read the shop's own catalog, price every product in it.

    Nobody hands the agent a product list — it asks the shop what it is selling.
    """
    from .connectors.fulfillment import make_fulfillment
    from .connectors.tiktok_shop_catalog import TikTokShopCatalog

    catalog = catalog if catalog is not None else TikTokShopCatalog(config)
    fulfillment = fulfillment if fulfillment is not None else make_fulfillment(config)
    resolved = []
    for product in catalog.list_products(limit=500):
        resolved.append(resolve_cost(
            product.get("design_id"), config, blank=product.get("blank"),
            catalog=catalog, fulfillment=fulfillment, manual_path=manual_path))
    return resolved
