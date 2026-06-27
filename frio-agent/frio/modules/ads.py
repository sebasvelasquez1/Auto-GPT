"""Ads capabilities — GATED example.

Demonstrates the gating + spend-cap invariant: ``ads.place_order`` stays
disabled until config approves live spend, and even then a real implementation
must check the spend ledger + a human approval before committing money.
"""

from __future__ import annotations

from ..capabilities import capability
from ..config import Config


@capability(
    "ads.place_order",
    "Launch a live TikTok ad campaign (commits real ad spend).",
    parameters={
        "campaign": {"type": "object", "description": "Campaign spec", "required": True},
        "budget_usd": {"type": "number", "description": "Daily budget", "required": True},
    },
    enabled=lambda c: c.ads_live_enabled and c.seller_approved,
    disabled_reason="TikTok Ads not approved / live spend disabled "
    "(set FRIO_ADS_LIVE_ENABLED=1 and FRIO_SELLER_APPROVED=1).",
    category="gated",
)
def place_order(campaign: dict, budget_usd: float, *, config: Config) -> dict:
    # Real impl (Phase 6): enforce spend caps against spend_ledger + HITL approval
    # BEFORE calling the TikTok Business API. Never let an LLM authorize spend.
    raise NotImplementedError("Phase 6: wire tiktok-business-api-sdk behind HITL + spend caps.")
