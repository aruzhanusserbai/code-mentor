"""Shared fixtures for the black-box ticket tests.

The tests talk to the service only over HTTP (see template/CONTRACT.md).
Set CODEMENTOR_BASE_URL to point them at another host.
"""

import os
import time

import pytest
import requests

DEFAULT_BASE_URL = "http://localhost:8080"
STARTUP_TIMEOUT_SECONDS = 90


def wait_until_up(base_url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{base_url}/actuator/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("CODEMENTOR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if not wait_until_up(url, STARTUP_TIMEOUT_SECONDS):
        pytest.fail(f"Service at {url} did not become healthy in {STARTUP_TIMEOUT_SECONDS}s")
    return url
