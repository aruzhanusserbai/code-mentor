"""Ticket 2: the order total must be the sum of unitPrice * quantity over all items."""

import json
from decimal import Decimal

import requests


def get_json(response: requests.Response) -> object:
    # Decimal keeps money values exact (no float rounding in comparisons).
    return json.loads(response.text, parse_float=Decimal)


def products_in_one_currency(base_url: str, count: int) -> list[dict]:
    """Return `count` products that share a currency (an order allows only one)."""
    products = get_json(requests.get(f"{base_url}/products", timeout=5))
    by_currency: dict[str, list[dict]] = {}
    for product in products:
        by_currency.setdefault(product["currency"], []).append(product)
    for same_currency in by_currency.values():
        if len(same_currency) >= count:
            return same_currency[:count]
    raise AssertionError(f"need {count} products with the same currency, got: {products}")


def create_order(base_url: str, lines: list[tuple[dict, int]]) -> dict:
    items = [{"productId": product["id"], "quantity": quantity} for product, quantity in lines]
    response = requests.post(f"{base_url}/orders", json={"items": items}, timeout=5)
    assert response.status_code == 201, f"expected 201, got {response.status_code}: {response.text}"
    return get_json(response)


def expected_total(lines: list[tuple[dict, int]]) -> Decimal:
    return sum((product["price"] * quantity for product, quantity in lines), Decimal("0"))


def assert_total(order: dict, lines: list[tuple[dict, int]]) -> None:
    expected = expected_total(lines)
    assert order["total"] == expected, (
        f"expected total {expected} (sum of unitPrice * quantity over {len(lines)} items), "
        f"got {order['total']}"
    )


def test_total_of_two_different_products(base_url: str) -> None:
    first, second = products_in_one_currency(base_url, 2)
    lines = [(first, 2), (second, 1)]

    order = create_order(base_url, lines)

    assert_total(order, lines)


def test_total_of_three_items_with_different_quantities(base_url: str) -> None:
    first, second, third = products_in_one_currency(base_url, 3)
    lines = [(first, 1), (second, 3), (third, 2)]

    order = create_order(base_url, lines)

    assert_total(order, lines)


def test_same_product_in_two_lines_is_counted_twice(base_url: str) -> None:
    (product,) = products_in_one_currency(base_url, 1)
    lines = [(product, 1), (product, 2)]

    order = create_order(base_url, lines)

    assert_total(order, lines)


def test_saved_order_has_the_same_total(base_url: str) -> None:
    first, second = products_in_one_currency(base_url, 2)
    lines = [(first, 1), (second, 1)]
    created = create_order(base_url, lines)

    response = requests.get(f"{base_url}/orders/{created['id']}", timeout=5)

    assert response.status_code == 200, f"expected 200, got {response.status_code}: {response.text}"
    assert_total(get_json(response), lines)


def test_single_item_order_is_still_correct(base_url: str) -> None:
    (product,) = products_in_one_currency(base_url, 1)
    lines = [(product, 3)]

    order = create_order(base_url, lines)

    assert_total(order, lines)
