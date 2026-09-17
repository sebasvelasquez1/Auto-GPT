"""Product sellability and ad efficiency are SEPARATE questions.

Design correction (2026-09-17), after the project owner rejected the earlier logic and
was right to: organic sales are evidence the market wants the product, so they must
never count against it. Ads extend reach to more people; they scale what organic
proved. What blended revenue genuinely cannot tell us is whether the ADS are efficient
— and the honest answer to that, absent evidence, is "unknown", reported beside the
product verdict rather than used to block it.
"""

from __future__ import annotations

from frio.ad_efficiency import MEASURED_LIFT, MEASURED_PAID, UNKNOWN, assess_ad_efficiency
from frio.config import Config
from frio.financials import CostStructure
from frio.modules.analyzer import analyze

CS = CostStructure(price=40.0, product_cost=10.0, fulfillment_cost=3.0,
                   platform_fee_pct=0.08)
CFG = Config(fin_min_units=5, fin_test_spend_usd=50.0, fin_scale_poas=1.5)


# --- The product verdict must not be punished for selling organically -------------

def test_organic_sales_do_not_block_a_scale_verdict() -> None:
    """The regression this whole module exists to prevent."""
    assert analyze(CS, units=60, ad_spend=100.0, config=CFG).decision == "scale"


def test_unmeasured_ads_are_disclosed_on_scale_but_never_change_the_verdict() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.6)
    v = analyze(CS, units=60, ad_spend=100.0, config=CFG, ad_efficiency=eff)
    assert v.decision == "scale"                      # verdict untouched
    assert v.ads is not None and v.ads["status"] == UNKNOWN
    assert any("UNMEASURED" in r for r in v.reasons)  # but the human is told


def test_inefficient_ads_still_do_not_veto_a_profitable_product() -> None:
    """A product that sells itself is still a good product, even if its ads are bad.
    Killing the ad is the optimize engine's job, not the product verdict's."""
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.6,
                               total_revenue=1000.0, organic_baseline_revenue=990.0)
    v = analyze(CS, units=60, ad_spend=100.0, config=CFG, ad_efficiency=eff)
    assert v.decision == "scale"
    assert v.ads["verdict"] == "inefficient"


# --- Tier 1: real paid attribution (Seller Center "Ads Gross Revenue") ------------

def test_paid_attributed_revenue_gives_a_clean_verdict() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               paid_revenue=400.0)
    assert eff.status == MEASURED_PAID
    assert eff.verdict == "efficient"
    assert round(eff.poas, 2) == 2.0                           # 400 * 0.5 / 100
    assert eff.basis == "paid_attributed_revenue"


def test_paid_attribution_can_also_say_the_ads_lose_money() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               paid_revenue=100.0)                 # 0.5x
    assert eff.verdict == "inefficient"
    assert "do NOT pay for themselves" in eff.headline


def test_paid_attribution_wins_over_an_available_baseline() -> None:
    """Preference order is deliberate: real attribution beats an inferred lift."""
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               paid_revenue=400.0, total_revenue=5000.0,
                               organic_baseline_revenue=0.0)
    assert eff.status == MEASURED_PAID


# --- Tier 2: incremental lift over a pre-ad baseline ------------------------------

def test_lift_over_baseline_measures_what_the_ads_added() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               total_revenue=900.0, organic_baseline_revenue=500.0)
    assert eff.status == MEASURED_LIFT
    assert round(eff.poas, 2) == 2.0          # (900-500) * 0.5 / 100
    assert eff.verdict == "efficient"


def test_no_lift_says_the_ads_added_nothing_and_says_it_is_not_the_products_fault() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               total_revenue=500.0, organic_baseline_revenue=520.0)
    assert eff.verdict == "inefficient"
    assert any("product may still sell fine" in r for r in eff.reasons)


def test_lift_discloses_that_it_is_an_estimate_not_attribution() -> None:
    """Honesty requirement: a lift can be moved by a demand trend or seasonality."""
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5,
                               total_revenue=900.0, organic_baseline_revenue=500.0)
    assert any("estimate" in r and "seasonal" in r for r in eff.reasons)


# --- Tier 3: no evidence means "unknown", never an optimistic default -------------

def test_blended_only_data_returns_unknown_with_no_invented_number() -> None:
    eff = assess_ad_efficiency(ad_spend=100.0, contribution_margin=0.5)
    assert eff.status == UNKNOWN and eff.verdict == "unknown"
    assert eff.poas is None
    assert any("does NOT count against the product" in r for r in eff.reasons)


def test_unknown_explains_both_remedies() -> None:
    reasons = " ".join(assess_ad_efficiency(ad_spend=10.0,
                                            contribution_margin=0.5).reasons)
    assert "Ads Gross Revenue" in reasons and "baseline" in reasons


def test_zero_ad_spend_is_undefined_not_efficient() -> None:
    eff = assess_ad_efficiency(ad_spend=0.0, contribution_margin=0.5,
                               paid_revenue=500.0)
    assert eff.status == UNKNOWN and eff.poas is None
