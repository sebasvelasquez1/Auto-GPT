"""Unit economics + product P&L (deterministic — no LLM in money math).

Computes the TRUE per-product economics the way DTC operators actually decide:
profit after COGS, fulfillment, platform fees, returns AND ad spend — not vanity
ROAS. Key outputs: contribution per unit, net profit, POAS, break-even ROAS.

References (2026): POAS = (Rev − COGS − fulfillment − fees − returns − ad) / ad;
1× POAS = break-even, ≥2× = scalable. Break-even ROAS = 1 / contribution margin.
TikTok Shop apparel referral ≈ 8% (incl. US payment processing).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostStructure:
    """Per-unit cost inputs for one product/design."""

    price: float                  # selling price per unit
    product_cost: float           # base item + print (POD) or supplier cost (dropship)
    fulfillment_cost: float = 0.0 # handling + shipping per unit
    platform_fee_pct: float = 0.08  # TikTok Shop referral (apparel ~8%, incl. US pay proc)
    payment_fee_pct: float = 0.0  # extra processing if not bundled
    affiliate_pct: float = 0.0    # creator commission, if affiliate-driven
    return_rate: float = 0.0      # fraction of orders returned/refunded (0..1)

    @property
    def fee_pct(self) -> float:
        return self.platform_fee_pct + self.payment_fee_pct + self.affiliate_pct

    def contribution_per_unit(self) -> float:
        """Profit per unit BEFORE ad spend. <= 0 means you lose money on every sale."""
        return (self.price * (1 - self.return_rate)
                - self.product_cost - self.fulfillment_cost
                - self.price * self.fee_pct)


@dataclass
class ProductPnL:
    units: int
    revenue: float
    ad_spend: float
    cogs: float
    fulfillment: float
    fees: float
    returns_cost: float
    contribution: float          # before ad spend
    net_profit: float            # after ad spend
    gross_margin: float
    contribution_margin: float
    net_margin: float
    contribution_per_unit: float
    roas: float | None           # revenue / ad spend
    poas: float | None           # contribution / ad spend (>=1 = ad break-even)
    break_even_roas: float | None
    cac: float | None            # ad spend / unit (cost per acquired sale)

    def snapshot(self) -> dict:
        def r(x):
            return round(x, 2) if x is not None else None
        return {
            "units": self.units, "revenue": r(self.revenue), "ad_spend": r(self.ad_spend),
            "cogs": r(self.cogs), "fulfillment": r(self.fulfillment), "fees": r(self.fees),
            "returns_cost": r(self.returns_cost), "contribution": r(self.contribution),
            "net_profit": r(self.net_profit), "gross_margin": r(self.gross_margin),
            "contribution_margin": r(self.contribution_margin), "net_margin": r(self.net_margin),
            "contribution_per_unit": r(self.contribution_per_unit),
            "roas": r(self.roas), "poas": r(self.poas),
            "break_even_roas": r(self.break_even_roas), "cac": r(self.cac),
        }


def compute_pnl(cs: CostStructure, units: int, ad_spend: float,
                revenue: float | None = None) -> ProductPnL:
    units = max(0, units)
    revenue = revenue if revenue is not None else units * cs.price
    cogs = units * cs.product_cost
    fulfillment = units * cs.fulfillment_cost
    fees = revenue * cs.fee_pct
    returns_cost = revenue * cs.return_rate
    contribution = revenue - cogs - fulfillment - fees - returns_cost
    net_profit = contribution - ad_spend

    gross_margin = (revenue - cogs) / revenue if revenue else 0.0
    contribution_margin = contribution / revenue if revenue else 0.0
    net_margin = net_profit / revenue if revenue else 0.0

    roas = revenue / ad_spend if ad_spend > 0 else None
    poas = contribution / ad_spend if ad_spend > 0 else None
    break_even_roas = 1 / contribution_margin if contribution_margin > 0 else None
    cac = ad_spend / units if units > 0 else None

    return ProductPnL(
        units=units, revenue=revenue, ad_spend=ad_spend, cogs=cogs,
        fulfillment=fulfillment, fees=fees, returns_cost=returns_cost,
        contribution=contribution, net_profit=net_profit, gross_margin=gross_margin,
        contribution_margin=contribution_margin, net_margin=net_margin,
        contribution_per_unit=cs.contribution_per_unit(), roas=roas, poas=poas,
        break_even_roas=break_even_roas, cac=cac)
