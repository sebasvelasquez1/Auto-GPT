"""SCALE must not fire on revenue that mixes paid and organic sales.

TikTok's own help centre (read 2026-09-16) defines GMV Max "Gross revenue" as "the
total gross revenue of TikTok Shop orders, both paid and organic, attributed to your
campaign", and warns that "ROI includes both organic and paid orders". Anything read
from Ads reporting is therefore NOT clean ad attribution, and POAS computed from it
overstates the ads' contribution.
"""

from __future__ import annotations

from frio.config import Config
from frio.financials import CostStructure
from frio.modules.analyzer import analyze

# Comfortable margins so the clean case lands squarely on SCALE.
CS = CostStructure(price=40.0, product_cost=10.0, fulfillment_cost=3.0,
                   platform_fee_pct=0.08)
CFG = Config(fin_min_units=5, fin_test_spend_usd=50.0, fin_scale_poas=1.5)


def _run(**kw):
    return analyze(CS, units=60, ad_spend=100.0, config=CFG, **kw)


def test_clean_revenue_still_scales() -> None:
    """The guard must not break the normal path."""
    assert _run().decision == "scale"


def test_contaminated_revenue_is_held_at_continue_not_scaled() -> None:
    verdict = _run(revenue_includes_organic=True)
    assert verdict.decision == "continue"
    assert any("SCALE vetoed" in r for r in verdict.reasons)
    assert any("ORGANIC" in r for r in verdict.reasons)


def test_veto_explains_the_remedy_not_just_the_refusal() -> None:
    """A non-technical owner reading the dashboard needs to know what to DO."""
    reasons = " ".join(_run(revenue_includes_organic=True).reasons)
    assert "Shop" in reasons


def test_cancel_is_not_vetoed_because_inflated_revenue_makes_a_loss_look_better() -> None:
    """Asymmetry: a cancel computed from optimistic revenue is conservative, so it
    stands. Only the spend-INCREASING verdict needs clean evidence."""
    loss = analyze(CS, units=6, ad_spend=500.0, config=CFG,
                   revenue_includes_organic=True)
    assert loss.decision == "cancel"


def test_structural_loss_is_unaffected_by_attribution() -> None:
    """Per-unit economics don't depend on who caused the sale."""
    bad = CostStructure(price=10.0, product_cost=12.0)
    assert analyze(bad, units=60, ad_spend=100.0, config=CFG,
                   revenue_includes_organic=True).decision == "cancel"
