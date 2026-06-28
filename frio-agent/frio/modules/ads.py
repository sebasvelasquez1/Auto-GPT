"""Phase 6 — Live ads + closed loop (MOST GATED + spend caps + HITL).

Launching and scaling campaigns spends real ad money, so:
  - capabilities stay disabled until ``ads_live_enabled`` AND ``seller_approved``;
  - every launch/scale needs explicit human approval;
  - every committed dollar passes the per-campaign + daily caps enforced against
    the append-only spend ledger (hard stop — the LLM can never override it).

The closed loop reads metrics -> optimize proposals, then applies them asymmetrically:
  - KILL  (reduces spend) -> auto-applied (pauses the campaign);
  - SCALE (increases spend) -> surfaced for human approval, never auto-applied.
"""

from __future__ import annotations

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.tiktok_ads import TikTokAdsConnector
from ..db.base import init_db, make_session_factory
from ..db.models import Campaign, Decision
from ..spend import SpendCapError, guard_and_record


def _launch_gate(config: Config, approve: bool) -> None:
    if not (config.ads_live_enabled and config.seller_approved):
        raise PermissionError(
            "live ad spend disabled — set FRIO_ADS_LIVE_ENABLED=1 and "
            "FRIO_SELLER_APPROVED=1 (and the per-campaign / daily spend caps).")
    if not approve:
        raise PermissionError(
            "launching/scaling a campaign requires explicit human approval (approve=True).")


def launch_campaign(name: str, daily_budget_usd: float, config: Config, *, approve: bool,
                    connector=None, database_url: str | None = None) -> dict:
    """Launch a campaign. GATED + HITL + spend caps."""
    _launch_gate(config, approve)
    connector = connector or TikTokAdsConnector(config)
    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        # Enforce caps BEFORE committing spend or calling the ad platform.
        guard_and_record(s, config, category="ads", amount=daily_budget_usd,
                         reference=f"launch:{name}",
                         per_item_cap=config.per_campaign_spend_cap_usd)
        external_id = connector.launch_campaign(name, daily_budget_usd)
        s.add(Campaign(external_id=external_id, name=name, status="active",
                       daily_budget_usd=daily_budget_usd, provider=connector.name))
        s.add(Decision(kind="launch", actor="human", target=name,
                       rationale="approved campaign launch",
                       payload={"campaign_id": external_id,
                                "daily_budget_usd": daily_budget_usd}))
        s.commit()
        return {"campaign_id": external_id, "name": name,
                "daily_budget_usd": daily_budget_usd, "provider": connector.name}


def scale_campaign(external_id: str, new_daily_budget_usd: float, config: Config, *,
                   approve: bool, connector=None, database_url: str | None = None) -> dict:
    """Raise a campaign's budget. GATED + HITL + spend caps (increases spend)."""
    _launch_gate(config, approve)
    if new_daily_budget_usd > config.per_campaign_spend_cap_usd:
        raise SpendCapError(
            f"new budget ${new_daily_budget_usd:.2f} exceeds per-campaign cap "
            f"${config.per_campaign_spend_cap_usd:.2f}")
    connector = connector or TikTokAdsConnector(config)
    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        camp = s.query(Campaign).filter_by(external_id=external_id).first()
        old = camp.daily_budget_usd if camp else 0.0
        delta = max(0.0, new_daily_budget_usd - old)
        # Only the *increase* commits new daily spend.
        guard_and_record(s, config, category="ads", amount=delta,
                         reference=f"scale:{external_id}",
                         per_item_cap=config.per_campaign_spend_cap_usd)
        if camp is not None:
            camp.daily_budget_usd = new_daily_budget_usd
        connector.set_budget(external_id, new_daily_budget_usd)
        s.add(Decision(kind="scale_applied", actor="human", target=external_id,
                       rationale="approved budget increase",
                       payload={"old": old, "new": new_daily_budget_usd, "delta": delta}))
        s.commit()
        return {"campaign_id": external_id, "old_budget": old,
                "new_budget": new_daily_budget_usd}


def run_closed_loop(config: Config, *, entity_type: str = "creative",
                    connector=None, database_url: str | None = None) -> dict:
    """metrics -> proposals -> auto-apply kills, surface scales for approval."""
    from .optimize import propose_all

    connector = connector or TikTokAdsConnector(config)
    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)

    applied_kills, pending_scales = 0, []
    with Session() as s:
        for p in propose_all(s, config, entity_type):
            if p.action == "kill":
                # Spend-reducing -> auto-apply (only touches the account if ads are live).
                if config.ads_live_enabled:
                    connector.pause_campaign(p.entity_id)
                s.add(Decision(kind="kill_applied", actor="engine", target=p.entity_id,
                               rationale=p.reason, payload={"auto": True}))
                applied_kills += 1
            elif p.action == "scale":
                # Spend-increasing -> never auto-applied; await human approval.
                pending_scales.append({"entity_id": p.entity_id, "reason": p.reason,
                                       "budget_change_pct": p.budget_change_pct})
                s.add(Decision(kind="scale_proposed", actor="engine", target=p.entity_id,
                               rationale=p.reason,
                               payload={"awaiting_approval": True,
                                        "budget_change_pct": p.budget_change_pct}))
        s.commit()
    return {"applied_kills": applied_kills, "pending_scales": pending_scales,
            "awaiting_approval": len(pending_scales)}


@capability(
    "ads.launch_campaign",
    "Launch a live TikTok ad campaign (commits real ad spend — gated + HITL + caps).",
    parameters={"name": {"type": "string", "required": True},
                "daily_budget_usd": {"type": "number", "required": True},
                "approve": {"type": "boolean", "required": True}},
    enabled=lambda c: c.ads_live_enabled and c.seller_approved,
    disabled_reason="Live ad spend disabled (set FRIO_ADS_LIVE_ENABLED=1, "
    "FRIO_SELLER_APPROVED=1, and FRIO_PER_CAMPAIGN_SPEND_CAP_USD / FRIO_DAILY_SPEND_CAP_USD).",
    category="gated",
)
def _cap_launch(name: str, daily_budget_usd: float, approve: bool,
                config: Config | None = None) -> dict:
    config = config or load_config()
    return launch_campaign(name, daily_budget_usd, config, approve=approve)


@capability(
    "ads.run_closed_loop",
    "Read metrics -> kill losers (auto) + propose scaling winners (needs approval).",
    parameters={"entity_type": {"type": "string", "required": False}},
    category="optimize",
)
def _cap_loop(entity_type: str = "creative", config: Config | None = None) -> dict:
    config = config or load_config()
    return run_closed_loop(config, entity_type=entity_type)
