"""Assertion helpers shared by ticket tests."""

import requests


def assert_error_body(response: requests.Response, expected_status: int) -> None:
    """Check the standard error format from CONTRACT.md."""
    assert response.status_code == expected_status, (
        f"expected HTTP {expected_status}, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("status") == expected_status, f"'status' field must be {expected_status}: {body}"
    error = body.get("error")
    assert isinstance(error, str) and error.strip(), f"'error' must be a non-empty string: {body}"
