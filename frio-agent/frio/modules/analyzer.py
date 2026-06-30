"""Commercial / financial analyzer — product viability (deterministic).

The business-level decision the optimize engine does NOT make: given a product's
true unit economics + real sales/ad spend, is this design/product worth continuing,
worth scaling, or should it be CANCELLED? Pure math + explicit rules — the LLM is
never in this path.

Verdicts:
  - CANCEL   — structurally unprofitable (lose money per unit) OR net loss after a
               fair test. (Distinct from the ad-level kill in optimize.py.)
  - WATCH    — not enough sales/spend yet to decide; keep testing.
  - CONTINUE — net-profitable (POAS > 1).
  - SCALE    — strongly profitable (POAS >= scale threshold).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..capabilities import capability
from ..config import Config, load_config
from ..db.base import make_session_factory
from ..financials import CostStructure, ProductPnL, compute_pnl
from ..metrics import aggregate_all


@dataclass
class Viability:
    decision: str            # cancel | watch | continue | scale
    headline: str
    reasons: list[str]
    pnl: dict


def assess_viability(pnl: ProductPnL, config: Config) -> Viability:
    reasons: list[str] = []

    # 1) Structural loss — lose money on every unit regardless of ads. Cancel.
    if pnl.contribution_per_unit <= 0:
        return Viability(
            "cancel", "Structurally unprofitable — lose money on every sale.",
            [f"Contribution per unit ${pnl.contribution_per_unit:.2f} <= 0 "
             f"(fix price/cost/fees BEFORE spending on ads)."], pnl.snapshot())

    if pnl.break_even_roas:
        reasons.append(f"Break-even ROAS = {pnl.break_even_roas:.2f}x "
                       f"(contribution margin {pnl.contribution_margin*100:.0f}%).")

    # 2) Not enough data to trust a verdict yet.
    if pnl.units < config.fin_min_units or pnl.ad_spend < config.fin_test_spend_usd:
        reasons.append(f"Only {pnl.units} sales / ${pnl.ad_spend:.0f} ad spend "
                       f"(need >= {config.fin_min_units} units & "
                       f"${config.fin_test_spend_usd:.0f} for a fair test).")
        return Viability("watch", "Keep testing — not enough data to decide.",
                         reasons, pnl.snapshot())

    # 3) Enough data: decide on real net profit / POAS.
    poas = pnl.poas if pnl.poas is not None else 0.0
    if pnl.net_profit > 0:
        if poas >= config.fin_scale_poas:
            return Viability(
                "scale", f"Strongly profitable — scale it (POAS {poas:.2f}x).",
                reasons + [f"Net profit ${pnl.net_profit:.2f} "
                           f"(net margin {pnl.net_margin*100:.0f}%); POAS "
                           f">= {config.fin_scale_poas:g}x."], pnl.snapshot())
        return Viability(
            "continue", f"Profitable — keep it (POAS {poas:.2f}x).",
            reasons + [f"Net profit ${pnl.net_profit:.2f} "
                       f"(net margin {pnl.net_margin*100:.0f}%)."], pnl.snapshot())

    return Viability(
        "cancel", "Net loss after a fair test — cancel this product.",
        reasons + [f"Net profit ${pnl.net_profit:.2f} (POAS {poas:.2f}x < 1) "
                   f"after ${pnl.ad_spend:.0f} ad spend."], pnl.snapshot())


def analyze(cs: CostStructure, units: int, ad_spend: float, config: Config | None = None,
            revenue: float | None = None) -> Viability:
    config = config or load_config()
    return assess_viability(compute_pnl(cs, units, ad_spend, revenue), config)


def cost_structure_from(config: Config, *, price: float, product_cost: float,
                        fulfillment_cost: float = 0.0, affiliate_pct: float = 0.0,
                        return_rate: float | None = None) -> CostStructure:
    """Build a CostStructure using config fee/return defaults."""
    return CostStructure(
        price=price, product_cost=product_cost, fulfillment_cost=fulfillment_cost,
        platform_fee_pct=config.fin_platform_fee_pct,
        payment_fee_pct=config.fin_payment_fee_pct, affiliate_pct=affiliate_pct,
        return_rate=config.fin_default_return_rate if return_rate is None else return_rate)


def analyze_listing_from_db(listing_id: str, cs: CostStructure, ad_spend: float,
                            config: Config | None = None,
                            database_url: str | None = None) -> Viability:
    """Pull a product's real sales (metrics_daily, entity_type='product') + assess."""
    config = config or load_config()
    Session = make_session_factory(database_url or config.database_url)
    with Session() as s:
        rows = [m for m in aggregate_all(s, entity_type="product")
                if m.entity_id == listing_id]
    units = rows[0].purchases if rows else 0
    revenue = rows[0].revenue_usd if rows else 0.0
    return analyze(cs, units, ad_spend, config, revenue=revenue)


@capability(
    "analyzer.product_viability",
    "Compute a product's true P&L (POAS/net profit) and a continue/scale/cancel verdict.",
    parameters={"price": {"type": "number", "required": True},
                "product_cost": {"type": "number", "required": True},
                "units": {"type": "integer", "required": True},
                "ad_spend": {"type": "number", "required": True}},
    category="optimize",
)
def _cap_viability(price: float, product_cost: float, units: int, ad_spend: float,
                   fulfillment_cost: float = 0.0, revenue: float | None = None,
                   config: Config | None = None) -> dict:
    config = config or load_config()
    cs = cost_structure_from(config, price=price, product_cost=product_cost,
                             fulfillment_cost=fulfillment_cost)
    return asdict(analyze(cs, units, ad_spend, config, revenue=revenue))
