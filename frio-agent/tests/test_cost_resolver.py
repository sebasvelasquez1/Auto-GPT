"""The agent derives product economics itself; manual entry is only the fallback.

Corrected design (2026-09-18): an autonomous agent reads the shop's own catalog and
works out whether each product makes money. It does not ask a human to type a product
list or a price. These tests pin that the automatic path is the primary one, that
manual entry only fills what no connector can supply, and that every figure declares
where it came from so a typed guess can never pass for live data.
"""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.cost_resolver import (
    FROM_CONFIG, FROM_FULFILLMENT, FROM_MANUAL, FROM_SHOP, resolve_all, resolve_cost,
)
from frio.product_costs import CostBook, MissingCostsError, ProductCost, save_costs

CFG = Config()


class FakeCatalog:
    def __init__(self, products): self._p = products
    def list_products(self, limit=50): return self._p[:limit]
    def price_for(self, sku):
        for p in self._p:
            if p["design_id"] == sku:
                return p.get("price")
        return None


class FakeFulfillment:
    def __init__(self, costs): self._c = costs
    def unit_cost_for(self, blank): return self._c.get(blank)


def _manual(tmp_path, *costs):
    book = CostBook()
    for c in costs:
        book.put(c)
    path = str(tmp_path / "manual.json")
    save_costs(book, path)
    return path


# --- The autonomous path ----------------------------------------------------------

def test_the_agent_reads_the_catalog_instead_of_being_handed_a_list(tmp_path) -> None:
    """Nobody passes in a product list — the shop is asked what it sells."""
    catalog = FakeCatalog([{"design_id": "a", "price": 30.0, "blank": "tee"},
                           {"design_id": "b", "price": 50.0, "blank": "hoodie"}])
    ful = FakeFulfillment({"tee": {"product_cost": 12.0, "shipping_cost": 4.0},
                           "hoodie": {"product_cost": 26.0, "shipping_cost": 7.0}})
    resolved = resolve_all(CFG, catalog=catalog, fulfillment=ful,
                           manual_path=_manual(tmp_path))
    assert [r.sku for r in resolved] == ["a", "b"]
    assert all(r.fully_automatic() for r in resolved)


def test_price_comes_from_the_shop_and_cost_from_the_fulfilment_provider(tmp_path) -> None:
    r = resolve_cost("a", CFG, blank="tee",
                     catalog=FakeCatalog([{"design_id": "a", "price": 30.0}]),
                     fulfillment=FakeFulfillment(
                         {"tee": {"product_cost": 12.0, "shipping_cost": 4.0}}),
                     manual_path=_manual(tmp_path))
    assert r.sources["price"] == FROM_SHOP
    assert r.sources["product_cost"] == FROM_FULFILLMENT
    assert r.sources["fees"] == FROM_CONFIG
    assert (r.price, r.product_cost, r.shipping_cost) == (30.0, 12.0, 4.0)


def test_the_resolved_numbers_drive_a_real_cost_structure(tmp_path) -> None:
    r = resolve_cost("a", CFG, blank="tee",
                     catalog=FakeCatalog([{"design_id": "a", "price": 30.0}]),
                     fulfillment=FakeFulfillment(
                         {"tee": {"product_cost": 12.0, "shipping_cost": 4.0}}),
                     manual_path=_manual(tmp_path))
    cs = r.to_cost_structure(CFG)
    assert cs.price == 30.0 and cs.fulfillment_cost == 4.0
    assert cs.platform_fee_pct == CFG.fin_platform_fee_pct
    assert round(cs.contribution_per_unit(), 2) == round(30.0 - 12.0 - 4.0 - 30.0 * 0.06, 2)


# --- Manual is a fallback, and is visibly marked as one ---------------------------

def test_manual_fills_only_what_no_connector_supplies(tmp_path) -> None:
    """Shop knows the price; nothing knows the cost -> only the cost is manual."""
    path = _manual(tmp_path, ProductCost(sku="a", product_cost=9.0, shipping_cost=2.0))
    r = resolve_cost("a", CFG, blank="unknown-blank",
                     catalog=FakeCatalog([{"design_id": "a", "price": 30.0}]),
                     fulfillment=FakeFulfillment({}), manual_path=path)
    assert r.sources["price"] == FROM_SHOP
    assert r.sources["product_cost"] == FROM_MANUAL
    assert r.complete()


def test_a_manual_number_is_never_mistaken_for_live_data(tmp_path) -> None:
    """fully_automatic() is what separates a derived figure from a typed one."""
    path = _manual(tmp_path, ProductCost(sku="a", product_cost=9.0))
    r = resolve_cost("a", CFG, blank="nope",
                     catalog=FakeCatalog([{"design_id": "a", "price": 30.0}]),
                     fulfillment=FakeFulfillment({}), manual_path=path)
    assert r.complete() and not r.fully_automatic()


def test_connectors_win_over_a_stale_manual_override(tmp_path) -> None:
    """Live data beats a number typed in weeks ago."""
    path = _manual(tmp_path, ProductCost(sku="a", price=1.0, product_cost=99.0))
    r = resolve_cost("a", CFG, blank="tee",
                     catalog=FakeCatalog([{"design_id": "a", "price": 30.0}]),
                     fulfillment=FakeFulfillment(
                         {"tee": {"product_cost": 12.0, "shipping_cost": 4.0}}),
                     manual_path=path)
    assert (r.price, r.product_cost) == (30.0, 12.0)


# --- No source, no invention ------------------------------------------------------

def test_nothing_anywhere_means_a_named_gap_not_a_guess(tmp_path) -> None:
    r = resolve_cost("ghost", CFG, catalog=FakeCatalog([]),
                     fulfillment=FakeFulfillment({}), manual_path=_manual(tmp_path))
    assert set(r.gaps) == {"price", "product_cost"}
    assert not r.complete()


def test_an_unresolved_product_refuses_to_produce_a_cost_structure(tmp_path) -> None:
    r = resolve_cost("ghost", CFG, catalog=FakeCatalog([]),
                     fulfillment=FakeFulfillment({}), manual_path=_manual(tmp_path))
    with pytest.raises(MissingCostsError, match="ghost"):
        r.to_cost_structure(CFG)


def test_a_zero_price_from_the_shop_is_a_gap_not_a_free_product(tmp_path) -> None:
    r = resolve_cost("a", CFG, blank="tee",
                     catalog=FakeCatalog([{"design_id": "a", "price": 0}]),
                     fulfillment=FakeFulfillment(
                         {"tee": {"product_cost": 12.0, "shipping_cost": 4.0}}),
                     manual_path=_manual(tmp_path))
    assert "price" in r.gaps


def test_the_shipped_offline_path_is_fully_automatic() -> None:
    """The real connectors on fixtures: proves the wiring, not just the fakes."""
    resolved = resolve_all(Config(), manual_path="does-not-exist.json")
    assert resolved and all(r.fully_automatic() for r in resolved)
