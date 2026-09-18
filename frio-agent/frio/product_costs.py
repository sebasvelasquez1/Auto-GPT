"""Per-product real costs — the numbers a verdict is only as good as.

Why this exists: the viability verdict ("does this product actually make money?") is
arithmetic on price, product cost, shipping and fees. Fees have defensible defaults;
PRICE and PRODUCT COST do not — they are specific to each design and blank, and no API
we have supplies both. Before this module the analyzer quietly fell back to config
defaults, so a product with no real numbers still produced a confident-looking verdict
built on fiction. That is worse than no verdict: it looks like an answer.

So the rule here is: **no real price and product cost, no verdict.** ``cost_structure_for``
raises ``MissingCostsError`` naming exactly which numbers are missing for which SKU,
and the dashboard shows "costs pending" instead of a fabricated P&L.

SCOPE (corrected 2026-09-18): this file is the FALLBACK, not the main path. An
autonomous agent derives these numbers itself — price from the shop listing, cost from
the fulfilment provider — see ``cost_resolver.py``. What lives here is the override for
whatever no connector can supply.

Fee defaults are verified, not guessed — see config.fin_platform_fee_pct.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass, field

from .config import Config
from .financials import CostStructure

COSTS_FILE = "product_costs.json"


class MissingCostsError(RuntimeError):
    """A product has no real price/cost on file, so no honest verdict is possible."""


@dataclass
class ProductCost:
    """What the owner has to supply once per product. Everything else is derived."""

    sku: str
    price: float | None = None            # what the buyer pays, from TikTok Shop
    product_cost: float | None = None     # blank + print (Printful) or supplier cost
    shipping_cost: float = 0.0            # per-unit shipping/handling you absorb
    blank: str | None = None              # which Printful item, so cost can be looked up
    affiliate_pct: float = 0.0            # creator commission, if affiliate-driven
    return_rate: float | None = None      # measured returns; None = use config default
    note: str = ""

    def missing(self) -> list[str]:
        """The fields with no honest default. Fees can be defaulted; these cannot."""
        gaps = []
        if self.price is None or self.price <= 0:
            gaps.append("price")
        if self.product_cost is None or self.product_cost < 0:
            gaps.append("product_cost")
        return gaps

    def complete(self) -> bool:
        return not self.missing()


@dataclass
class CostBook:
    products: dict[str, ProductCost] = field(default_factory=dict)

    def get(self, sku: str) -> ProductCost:
        return self.products.get(sku, ProductCost(sku=sku))

    def put(self, cost: ProductCost) -> None:
        self.products[cost.sku] = cost

    def incomplete(self) -> list[ProductCost]:
        return [c for c in self.products.values() if not c.complete()]


def load_costs(path: str = COSTS_FILE) -> CostBook:
    """Read the cost book. A missing file is an empty book, not an error — a fresh
    install has no costs yet, and the caller's job is to ask for them."""
    target = pathlib.Path(path)
    if not target.exists():
        return CostBook()
    raw = json.loads(target.read_text() or "{}")
    return CostBook(products={
        sku: ProductCost(sku=sku, **{k: v for k, v in body.items() if k != "sku"})
        for sku, body in raw.get("products", {}).items()})


def save_costs(book: CostBook, path: str = COSTS_FILE) -> str:
    """Written as readable JSON on purpose: the owner may well edit it by hand."""
    payload = {"products": {sku: {k: v for k, v in asdict(c).items() if k != "sku"}
                            for sku, c in sorted(book.products.items())}}
    target = pathlib.Path(path)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return str(target)


def cost_structure_for(sku: str, config: Config, *,
                       path: str = COSTS_FILE) -> CostStructure:
    """Build the P&L inputs for one product — or refuse, saying what is missing.

    Refusing is the point. An invented price produces an invented verdict, and this
    verdict is what decides whether real money goes behind a product.
    """
    cost = load_costs(path).get(sku)
    gaps = cost.missing()
    if gaps:
        raise MissingCostsError(
            f"product {sku!r} is missing {' and '.join(gaps)} — no verdict can be "
            f"computed without them. Set them with: frio costs set --sku {sku} "
            f"--price <what the buyer pays> --product-cost <what it costs you>")
    return CostStructure(
        price=cost.price, product_cost=cost.product_cost,
        fulfillment_cost=cost.shipping_cost,
        platform_fee_pct=config.fin_platform_fee_pct,
        payment_fee_pct=config.fin_payment_fee_pct,
        affiliate_pct=cost.affiliate_pct,
        return_rate=(config.fin_default_return_rate if cost.return_rate is None
                     else cost.return_rate))
