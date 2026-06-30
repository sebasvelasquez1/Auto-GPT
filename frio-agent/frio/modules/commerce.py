"""Phase 5 — Commerce / fulfillment (GATED + HITL).

Publishing a listing and creating an order are outward, money-adjacent actions,
so they stay disabled until ``seller_approved`` and require explicit human
approval every time. POD (Printful) and Dropship (CJ) plug in via the shared
``Fulfillment`` interface. Selling-side actions sync back into ``metrics_daily``
so the optimize engine can read real results.
"""

from __future__ import annotations

from ..capabilities import capability
from ..config import Config, load_config
from ..connectors.fulfillment import make_fulfillment
from ..db.base import init_db, make_session_factory
from ..db.models import Decision, MetricsDaily, Product
from ..interfaces import Fulfillment, ProductCandidate


def _require_gate(config: Config, approve: bool) -> None:
    if not config.seller_approved:
        raise PermissionError(
            "commerce is disabled — set FRIO_SELLER_APPROVED=1 once your TikTok "
            "Shop seller account + app are approved.")
    if not approve:
        raise PermissionError(
            "this outward action requires explicit human approval (approve=True / --approve).")


def publish_product(product: dict, config: Config, *, approve: bool,
                    fulfillment: Fulfillment | None = None,
                    database_url: str | None = None) -> dict:
    """Create the live listing. GATED + HITL."""
    _require_gate(config, approve)
    fulfillment = fulfillment or make_fulfillment(config)
    candidate = ProductCandidate(**product)
    listing_id = fulfillment.publish_product(candidate)  # may refuse non-compliant dropship

    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        row = (s.query(Product)
               .filter_by(title=candidate.title, kind=candidate.kind).first())
        if row is not None:
            row.external_id = listing_id
        s.add(Decision(kind="publish", actor="human", target=candidate.title,
                       rationale="approved listing publish",
                       payload={"listing_id": listing_id, "provider": fulfillment.name,
                                "pipeline": config.pipeline}))
        s.commit()
    return {"listing_id": listing_id, "provider": fulfillment.name,
            "product": candidate.title, "pipeline": config.pipeline}


def create_order(listing_id: str, address: dict, config: Config, *, approve: bool,
                 fulfillment: Fulfillment | None = None,
                 database_url: str | None = None) -> dict:
    """Produce/ship one order. GATED + HITL."""
    _require_gate(config, approve)
    fulfillment = fulfillment or make_fulfillment(config)
    result = fulfillment.create_order(listing_id, address)

    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        s.add(Decision(kind="order", actor="human", target=listing_id,
                       rationale="approved order fulfillment",
                       payload={"order_id": result.external_order_id,
                                "status": result.status, "provider": fulfillment.name}))
        s.commit()
    return {"order_id": result.external_order_id, "status": result.status,
            "provider": fulfillment.name}


def sync_sales(listing_id: str, config: Config, *, orders: list[dict] | None = None,
               ad_spend: float = 0.0, database_url: str | None = None) -> dict:
    """Pull shop sales (+ associated ad spend) for a listing into metrics_daily.

    This feeds BOTH the optimize engine and the financial analyzer — the analyzer
    reads this same row's spend_usd as the product's ad spend automatically. GATED
    (needs shop access). Offline synthesizes a small order set so the loop can be
    demonstrated end-to-end.
    """
    if not config.seller_approved:
        raise PermissionError("commerce disabled — set FRIO_SELLER_APPROVED=1.")

    if orders is None:  # offline synthetic sales
        orders = [{"purchases": 3, "revenue_usd": 75.0}]

    purchases = sum(o["purchases"] for o in orders)
    revenue = sum(o["revenue_usd"] for o in orders)

    database_url = database_url or config.database_url
    init_db(database_url)
    Session = make_session_factory(database_url)
    with Session() as s:
        s.add(MetricsDaily(entity_type="product", entity_id=listing_id,
                           purchases=purchases, revenue_usd=revenue, spend_usd=ad_spend))
        s.add(Decision(kind="sync_sales", actor="engine", target=listing_id,
                       rationale="synced shop sales + ad spend into metrics",
                       payload={"orders": len(orders), "purchases": purchases,
                                "revenue_usd": revenue, "ad_spend": ad_spend}))
        s.commit()
    return {"listing_id": listing_id, "orders": len(orders), "purchases": purchases,
            "revenue_usd": revenue, "ad_spend": ad_spend}


@capability(
    "commerce.publish_product",
    "Publish a product listing to the store (outward action — gated + HITL).",
    parameters={"product": {"type": "object", "required": True},
                "approve": {"type": "boolean", "required": True}},
    enabled=lambda c: c.seller_approved,
    disabled_reason="Commerce disabled (set FRIO_SELLER_APPROVED=1 once your TikTok "
    "Shop seller account + app are approved).",
    category="gated",
)
def _cap_publish(product: dict, approve: bool, config: Config | None = None) -> dict:
    config = config or load_config()
    return publish_product(product, config, approve=approve)


@capability(
    "commerce.create_order",
    "Produce/ship one order (gated + HITL).",
    parameters={"listing_id": {"type": "string", "required": True},
                "address": {"type": "object", "required": True},
                "approve": {"type": "boolean", "required": True}},
    enabled=lambda c: c.seller_approved,
    disabled_reason="Commerce disabled (set FRIO_SELLER_APPROVED=1).",
    category="gated",
)
def _cap_order(listing_id: str, address: dict, approve: bool,
               config: Config | None = None) -> dict:
    config = config or load_config()
    return create_order(listing_id, address, config, approve=approve)


@capability(
    "commerce.sync_sales",
    "Sync shop sales for a listing into metrics_daily (gated).",
    parameters={"listing_id": {"type": "string", "required": True}},
    enabled=lambda c: c.seller_approved,
    disabled_reason="Commerce disabled (set FRIO_SELLER_APPROVED=1).",
    category="gated",
)
def _cap_sync(listing_id: str, config: Config | None = None) -> dict:
    config = config or load_config()
    return sync_sales(listing_id, config)
