"""Problem 6: the agent's lookup tools answer from the database and never invent."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REAL_DATA = _HERE.parent.parent / "data"
_TMP = Path(tempfile.mkdtemp(prefix="cc-tools-test-"))
shutil.copy(_REAL_DATA / "campus_customs.db", _TMP / "campus_customs.db")
(_TMP / "products").mkdir()
os.environ["DATA_DIR"] = str(_TMP)

import db  # noqa: E402
from agent import unverified_prices  # noqa: E402
from models import ProductSummary  # noqa: E402
from tools import lookup_product, lookup_search, lookup_size, lookup_stock, price_display  # noqa: E402

HOODIE = "basic-hoodie-big-yale"


def _db_quantity(product_id: str, size: str) -> int:
    with db.connect() as con:
        row = con.execute("SELECT quantity FROM inventory WHERE product_id=? AND size=?", (product_id, size)).fetchone()
    return int(row["quantity"])


def test_price_display_matches_database():
    result = lookup_product(HOODIE)
    assert result.ok and result.product is not None
    with db.connect() as con:
        price = float(con.execute("SELECT price FROM catalogue WHERE product_id=?", (HOODIE,)).fetchone()["price"])
    assert result.product.price == price
    assert result.price_display == price_display(price) == "$68"


def test_search_returns_real_items_with_prices_and_sizes():
    result, covered = lookup_search("bulldog", category="hoodie")
    assert result.ok and result.total_matches >= 1
    assert [b.product_id for b in result.items] == [p.product_id for p in covered]
    for b in result.items:
        assert db.get_product(b.product_id) is not None
        assert b.price_display.startswith("$")
        assert set(b.sizes_in_stock).isdisjoint(b.sold_out_sizes)


def test_cheapest_sort_is_ascending_and_capped():
    result, _ = lookup_search("", category="t-shirt", sort="price_asc")
    prices = [b.price for b in result.items]
    assert prices == sorted(prices)
    assert len(result.items) <= 8 and result.total_matches >= len(result.items)


def test_stock_by_size_reports_sold_out_sizes_plainly():
    # Find a product with at least one empty size in the shipped data.
    with db.connect() as con:
        row = con.execute("SELECT product_id, size FROM inventory WHERE quantity = 0 LIMIT 1").fetchone()
    pid, empty_size = row["product_id"], row["size"]
    result = lookup_stock(pid)
    assert result.ok
    assert empty_size in result.sold_out_sizes and empty_size not in result.sizes_in_stock
    entry = next(s for s in result.sizes if s.size == empty_size)
    assert entry.status == "sold_out" and entry.label == "Sold out" and entry.quantity == 0
    assert result.total_stock == sum(s.quantity for s in result.sizes)


def test_one_size_check_matches_database_and_lists_alternatives():
    result = lookup_size(HOODIE, "M")
    assert result.ok and result.quantity == _db_quantity(HOODIE, "M")
    assert result.status in ("in_stock", "low", "sold_out")
    assert "M" not in result.other_sizes_in_stock


def test_unknown_product_is_an_error_not_a_guess():
    assert lookup_product("ghost-hoodie").ok is False
    assert lookup_stock("").ok is False
    bad = lookup_size("nope", "L")
    assert bad.ok is False and bad.quantity is None and "search_products" in (bad.error or "")


def test_price_check_flags_amounts_not_from_tools():
    seen = {HOODIE: ProductSummary.model_validate({**lookup_product(HOODIE).product.model_dump()})}
    assert unverified_prices("The Basic Hoodie Big Yale is $68.", seen) == []
    assert unverified_prices("It is $59.99 today!", seen) == ["$59.99"]
    assert unverified_prices("10% off one item", seen) == []
