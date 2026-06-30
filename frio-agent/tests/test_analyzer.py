"""Commercial/financial analyzer tests — the money math gets exact-number coverage."""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.financials import CostStructure, compute_pnl
from frio.modules.analyzer import (
    all_product_verdicts,
    analyze,
    analyze_listing_from_db,
    cost_structure_from,
)

CFG = Config()  # fee 8%, target POAS 1.5, scale 2.0, min 10 units / $50 spend


def _cs(price=30.0, cost=9.0, ful=5.0, **kw) -> CostStructure:
    return CostStructure(price=price, product_cost=cost, fulfillment_cost=ful,
                         platform_fee_pct=0.08, **kw)


def test_compute_pnl_exact_numbers() -> None:
    p = compute_pnl(_cs(), units=40, ad_spend=120)
    assert p.revenue == 1200
    assert round(p.contribution_per_unit, 2) == 13.60   # 30 - 9 - 5 - 2.4
    assert round(p.contribution, 2) == 544.0            # 1200 - 360 - 200 - 96
    assert round(p.net_profit, 2) == 424.0              # 544 - 120
    assert round(p.poas, 2) == 4.53                     # 544 / 120
    assert round(p.roas, 2) == 10.0
    assert round(p.break_even_roas, 2) == 2.21          # 1 / 0.4533
    assert round(p.cac, 2) == 3.0


def test_structural_loss_is_cancel() -> None:
    # price too low: lose money on every unit regardless of ads
    v = analyze(_cs(price=12.0), units=100, ad_spend=500, config=CFG)
    assert v.decision == "cancel"
    assert "every sale" in v.headline.lower()


def test_insufficient_data_is_watch() -> None:
    v = analyze(_cs(), units=3, ad_spend=20, config=CFG)
    assert v.decision == "watch"


def test_strong_profit_is_scale() -> None:
    v = analyze(_cs(), units=40, ad_spend=120, config=CFG)  # POAS 4.5x
    assert v.decision == "scale"
    assert v.pnl["net_profit"] == 424.0


def test_modest_profit_is_continue() -> None:
    v = analyze(_cs(), units=20, ad_spend=250, config=CFG)  # POAS ~1.09x
    assert v.decision == "continue"
    assert v.pnl["net_profit"] > 0


def test_net_loss_after_fair_test_is_cancel() -> None:
    v = analyze(_cs(), units=15, ad_spend=300, config=CFG)  # POAS 0.68x
    assert v.decision == "cancel"
    assert "net loss" in v.headline.lower()


def test_fees_and_returns_reduce_contribution() -> None:
    base = compute_pnl(_cs(), units=10, ad_spend=0)
    with_returns = compute_pnl(_cs(return_rate=0.2), units=10, ad_spend=0)
    assert with_returns.contribution < base.contribution


def test_analyze_listing_from_db(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'a.db'}"
    from frio.db.base import init_db, make_session_factory
    from frio.db.models import MetricsDaily

    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        s.add(MetricsDaily(entity_type="product", entity_id="listing-1",
                           purchases=40, revenue_usd=1200.0))
        s.commit()

    v = analyze_listing_from_db("listing-1", _cs(), ad_spend=120,
                                config=Config(database_url=url), database_url=url)
    assert v.decision == "scale" and v.pnl["units"] == 40


def test_analyze_listing_pulls_ad_spend_from_synced_metrics(tmp_path) -> None:
    # No explicit ad_spend -> taken from metrics_daily.spend_usd automatically.
    url = f"sqlite:///{tmp_path/'b.db'}"
    from frio.db.base import init_db, make_session_factory
    from frio.db.models import MetricsDaily

    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        s.add(MetricsDaily(entity_type="product", entity_id="listing-2",
                           purchases=40, revenue_usd=1200.0, spend_usd=120.0))
        s.commit()

    v = analyze_listing_from_db("listing-2", _cs(), config=Config(database_url=url),
                                database_url=url)
    assert v.pnl["ad_spend"] == 120.0 and v.decision == "scale"


def test_all_product_verdicts_only_priced_products_worst_first(tmp_path) -> None:
    url = f"sqlite:///{tmp_path/'c.db'}"
    from frio.db.base import init_db, make_session_factory
    from frio.db.models import MetricsDaily, Product

    init_db(url)
    Session = make_session_factory(url)
    with Session() as s:
        winner = Product(kind="pod", title="Winner", source="existing-catalog",
                         price=30.0, unit_cost=9.0, fulfillment_unit_cost=5.0,
                         metadata_={"blank": "tank top"})
        loser = Product(kind="pod", title="Loser", source="existing-catalog",
                        price=12.0, unit_cost=9.0, fulfillment_unit_cost=5.0,
                        metadata_={"blank": "tee"})
        unpriced = Product(kind="pod", title="Unpriced", source="existing-catalog")
        s.add_all([winner, loser, unpriced])
        s.commit()
        s.add(MetricsDaily(entity_type="product", entity_id=str(winner.id),
                           purchases=40, revenue_usd=1200.0, spend_usd=120.0))
        s.add(MetricsDaily(entity_type="product", entity_id=str(loser.id),
                           purchases=15, revenue_usd=180.0, spend_usd=300.0))
        s.commit()

    rows = all_product_verdicts(Config(database_url=url), database_url=url)
    titles = [r.title for r in rows]
    assert "Unpriced" not in titles            # only priced products are assessed
    assert titles == ["Loser", "Winner"]        # worst-first ordering
    assert rows[0].viability.decision == "cancel"
    assert rows[1].viability.decision == "scale"
