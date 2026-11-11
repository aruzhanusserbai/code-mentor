"""Ticket 1: checkout with an empty cart must return 400, not 500."""

import requests

from helpers import assert_error_body


def post_order(base_url: str, body: dict) -> requests.Response:
    return requests.post(f"{base_url}/orders", json=body, timeout=5)


def test_empty_items_returns_400(base_url: str) -> None:
    response = post_order(base_url, {"items": []})

    assert_error_body(response, 400)


def test_missing_items_returns_400(base_url: str) -> None:
    response = post_order(base_url, {})

    assert_error_body(response, 400)


def test_valid_order_is_still_created(base_url: str) -> None:
    product = requests.get(f"{base_url}/products", timeout=5).json()[0]

    response = post_order(base_url, {"items": [{"productId": product["id"], "quantity": 1}]})

    assert response.status_code == 201, f"expected 201, got {response.status_code}: {response.text}"
    order = response.json()
    assert order["status"] == "CREATED"
    assert [item["productId"] for item in order["items"]] == [product["id"]]
