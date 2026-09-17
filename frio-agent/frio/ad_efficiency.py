"""Is the ADVERTISING working? — kept deliberately separate from "does the product sell?"

Why this module exists (design correction, 2026-09-17, on the project owner's
challenge — he was right and the earlier code was wrong):

An earlier version vetoed the product-level SCALE verdict whenever revenue included
organic sales. That conflated two different questions. Organic sales are *evidence that
the market wants the product* — arguably the cleanest evidence there is, since nobody
was paid to show it to anyone. Blocking a scale decision because a product also sells
organically punishes the product for being good. Ads then extend reach to more people;
they scale what organic proved.

The real question that blended revenue cannot answer is a narrower one: **are the ads
themselves efficient?** That is an ad-budget question, not a product question, and it
gets its own answer here — including an explicit "unknown", which is the honest output
when the data cannot support a claim. It never blocks the product verdict.

Why blended data cannot answer it (TikTok's own words, read first-hand 2026-09-16/17):
  - GMV Max "Gross revenue" = "The total gross revenue of TikTok Shop orders, both paid
    and organic, attributed to your campaign."
  - "If a customer purchases Product A while the GMV Max campaign is active, but doesn't
    view or click on any ads, the purchase will be attributed to GMV Max."
    -> During a GMV Max campaign, essentially ALL sales of that product are credited to
    the campaign. That is a campaign-window total, not an attribution.

Two real ways out, both implemented below, best first:
  1. PAID-ATTRIBUTED REVENUE. TikTok Seller Center's Data Compass reports
     "Ads Gross Revenue" ("Sales attributed to ads") separately from
     "Non-Ads Gross Revenue" ("Sales not attributed to Ads"), on a 7-day-click /
     1-day-view window. This is Shop-side data, not available from Ads reporting.
  2. INCREMENTAL LIFT. With an organic baseline from before the campaign, the lift
     (revenue now - baseline) is what the ads added. This is the same idea TikTok
     itself invokes when it describes GMV Max as optimizing for "incremental GMV",
     and it needs no paid/organic split — only history we already store.

Sources: ads.tiktok.com/help — "How to view reporting for your Product GMV Max
campaign", "About attribution for GMV Max", "About Ads Metrics in Seller Center".
See knowledge/investigacion/2026-09-medir-ads-tiktok-shop.md.
"""

from __future__ import annotations

from dataclasses import dataclass

MEASURED_PAID = "measured_paid"
MEASURED_LIFT = "measured_lift"
UNKNOWN = "unknown"


@dataclass
class AdEfficiency:
    """A read on the ads, never a gate on the product."""

    status: str                  # measured_paid | measured_lift | unknown
    verdict: str                 # efficient | inefficient | unknown
    headline: str
    reasons: list[str]
    poas: float | None = None    # contribution attributable to ads / ad spend
    basis: str | None = None     # which revenue figure the poas came from

    def snapshot(self) -> dict:
        return {"status": self.status, "verdict": self.verdict,
                "headline": self.headline, "reasons": list(self.reasons),
                "poas": round(self.poas, 2) if self.poas is not None else None,
                "basis": self.basis}


def assess_ad_efficiency(*, ad_spend: float, contribution_margin: float,
                         paid_revenue: float | None = None,
                         total_revenue: float | None = None,
                         organic_baseline_revenue: float | None = None,
                         break_even_poas: float = 1.0) -> AdEfficiency:
    """Judge the ads on whatever evidence actually exists — and say so when none does.

    Profit is measured on CONTRIBUTION (revenue minus product, fulfilment and fee
    costs), not on revenue, because revenue that does not cover its own cost of goods
    is not a win. ``contribution_margin`` comes from the product's own P&L, and is
    applied to the ad-attributable revenue: the assumption is that an ad-driven sale
    has the same unit economics as any other sale of that product, which holds for a
    single product at a single price.

    Preference order is deliberate: real paid attribution beats an inferred lift, and
    an inferred lift beats a guess. There is no fourth tier — no evidence means
    ``unknown``, not an optimistic default.
    """
    if ad_spend <= 0:
        return AdEfficiency(
            UNKNOWN, "unknown", "No ad spend yet — nothing to judge.",
            ["Ad efficiency is undefined with zero ad spend."])

    # Tier 1 — real paid attribution (Shop-side "Ads Gross Revenue").
    if paid_revenue is not None:
        poas = (paid_revenue * contribution_margin) / ad_spend
        efficient = poas >= break_even_poas
        return AdEfficiency(
            MEASURED_PAID, "efficient" if efficient else "inefficient",
            (f"Ads {'pay for themselves' if efficient else 'do NOT pay for themselves'} "
             f"on paid-attributed sales (POAS {poas:.2f}x)."),
            [f"Paid-attributed revenue ${paid_revenue:.2f} x contribution margin "
             f"{contribution_margin*100:.0f}% / ${ad_spend:.2f} ad spend = {poas:.2f}x.",
             "Basis: Seller Center 'Ads Gross Revenue' (sales attributed to ads), "
             "which is the clean measure — organic sales are excluded."],
            poas=poas, basis="paid_attributed_revenue")

    # Tier 2 — incremental lift over a pre-campaign organic baseline.
    if total_revenue is not None and organic_baseline_revenue is not None:
        lift = total_revenue - organic_baseline_revenue
        poas = (lift * contribution_margin) / ad_spend
        efficient = poas >= break_even_poas
        if lift <= 0:
            return AdEfficiency(
                MEASURED_LIFT, "inefficient",
                "Ads added nothing measurable — sales are at or below the pre-ad baseline.",
                [f"Revenue ${total_revenue:.2f} vs organic baseline "
                 f"${organic_baseline_revenue:.2f} = no lift.",
                 "The product may still sell fine on its own; this says the ADS are not "
                 "adding to it. Judge the product on its own verdict, not on this."],
                poas=poas, basis="incremental_lift")
        return AdEfficiency(
            MEASURED_LIFT, "efficient" if efficient else "inefficient",
            (f"Ads {'add more than they cost' if efficient else 'add less than they cost'} "
             f"(incremental POAS {poas:.2f}x)."),
            [f"Lift = ${total_revenue:.2f} now - ${organic_baseline_revenue:.2f} "
             f"baseline = ${lift:.2f}.",
             f"Lift x contribution margin {contribution_margin*100:.0f}% / "
             f"${ad_spend:.2f} ad spend = {poas:.2f}x.",
             "Basis: incremental lift over the pre-ad baseline — an estimate, not a "
             "clean attribution. A demand trend or a seasonal swing would also move it."],
            poas=poas, basis="incremental_lift")

    # Tier 3 — no evidence. Say so plainly; do NOT invent a number.
    return AdEfficiency(
        UNKNOWN, "unknown",
        "Cannot tell whether the ads are working — the revenue data is blended.",
        ["TikTok's Ads reporting credits a GMV Max campaign with ALL sales of the "
         "product while it runs, including sales from people who never saw an ad, so "
         "revenue / ad spend does not measure the ads.",
         "This does NOT count against the product: organic sales are real evidence the "
         "product sells. It only means the ADS are unmeasured.",
         "To measure them: connect TikTok Shop and read Seller Center's 'Ads Gross "
         "Revenue' (sales attributed to ads), or record an organic baseline before the "
         "next campaign so the lift can be computed."])
