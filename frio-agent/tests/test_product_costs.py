"""Real costs, or no verdict. No invented price, no invented verdict."""

from __future__ import annotations

import pytest

from frio.config import Config
from frio.product_costs import (
    CostBook, MissingCostsError, ProductCost, cost_structure_for, load_costs, save_costs,
)

CFG = Config()


def _book(tmp_path, *costs):
    book = CostBook()
    for c in costs:
        book.put(c)
    path = str(tmp_path / "costs.json")
    save_costs(book, path)
    return path


def test_a_product_with_no_costs_is_refused_not_estimated(tmp_path) -> None:
    """The whole point: a confident verdict from fabricated numbers is worse than none."""
    path = _book(tmp_path)
    with pytest.raises(MissingCostsError) as exc:
        cost_structure_for("tee-luna", CFG, path=path)
    assert "price and product_cost" in str(exc.value)
    assert "tee-luna" in str(exc.value)


def test_the_refusal_tells_the_owner_the_exact_command_to_fix_it(tmp_path) -> None:
    """A non-technical owner needs the remedy, not just the complaint."""
    with pytest.raises(MissingCostsError, match="frio costs set --sku tee-luna"):
        cost_structure_for("tee-luna", CFG, path=str(tmp_path / "none.json"))


def test_a_partially_filled_product_is_still_refused(tmp_path) -> None:
    path = _book(tmp_path, ProductCost(sku="tee-luna", price=29.99))
    with pytest.raises(MissingCostsError, match="missing product_cost"):
        cost_structure_for("tee-luna", CFG, path=path)


def test_complete_costs_build_a_real_cost_structure(tmp_path) -> None:
    path = _book(tmp_path, ProductCost(sku="tee-luna", price=29.99, product_cost=12.40,
                                       shipping_cost=4.50, affiliate_pct=0.1))
    cs = cost_structure_for("tee-luna", CFG, path=path)
    assert cs.price == 29.99 and cs.product_cost == 12.40
    assert cs.fulfillment_cost == 4.50 and cs.affiliate_pct == 0.1
    assert cs.platform_fee_pct == CFG.fin_platform_fee_pct
    assert cs.contribution_per_unit() > 0


def test_zero_or_negative_price_counts_as_missing(tmp_path) -> None:
    """A free product is not a priced product; treat it as unset rather than valid."""
    path = _book(tmp_path, ProductCost(sku="x", price=0.0, product_cost=5.0))
    with pytest.raises(MissingCostsError, match="missing price"):
        cost_structure_for("x", CFG, path=path)


def test_costs_round_trip_through_the_file(tmp_path) -> None:
    path = _book(tmp_path, ProductCost(sku="a", price=10.0, product_cost=4.0,
                                       note="pilot design"))
    reloaded = load_costs(path)
    assert reloaded.get("a").price == 10.0
    assert reloaded.get("a").note == "pilot design"


def test_a_missing_file_is_an_empty_book_not_a_crash(tmp_path) -> None:
    assert load_costs(str(tmp_path / "nope.json")).products == {}


def test_incomplete_lists_exactly_what_is_blocked(tmp_path) -> None:
    book = load_costs(_book(
        tmp_path,
        ProductCost(sku="ready", price=20.0, product_cost=8.0),
        ProductCost(sku="blocked", price=20.0)))
    assert [c.sku for c in book.incomplete()] == ["blocked"]


def test_platform_fee_default_matches_tiktoks_published_us_rate() -> None:
    """6% is TikTok's own published US referral fee for most categories (2024-04-01).
    Pinned because an earlier 0.08 had no source, and an overstated fee makes every
    product look worse than it is while an understated one makes it look better."""
    assert Config().fin_platform_fee_pct == 0.06
