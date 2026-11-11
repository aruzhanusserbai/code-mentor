"""Ticket 0: the service runs and GET /products/{id} exists."""

import requests

from helpers import assert_error_body

MISSING_PRODUCT_ID = 999999


def test_health_is_up(base_url: str) -> None:
    response = requests.get(f"{base_url}/actuator/health", timeout=5)

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_get_product_by_id_returns_product(base_url: str) -> None:
    products = requests.get(f"{base_url}/products", timeout=5).json()
    expected = products[0]

    response = requests.get(f"{base_url}/products/{expected['id']}", timeout=5)

    assert response.status_code == 200, f"GET /products/{expected['id']} returned {response.status_code}"
    assert response.json() == expected


def test_get_missing_product_returns_404(base_url: str) -> None:
    response = requests.get(f"{base_url}/products/{MISSING_PRODUCT_ID}", timeout=5)

    assert_error_body(response, 404)
