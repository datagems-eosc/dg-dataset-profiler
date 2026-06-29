"""Shared fixtures for the API integration tests.

These tests require the API stack from ``docker-compose-dev.yml`` to be running
and reachable at ``config.BASE_URL``. If it is not reachable, the whole module is
skipped rather than failed, so a normal unit-test run is unaffected.
"""
import pytest
import requests

from integration_tests import config
from integration_tests.client import ProfilerClient


@pytest.fixture(scope="session")
def client() -> ProfilerClient:
    """A ProfilerClient pointed at the running API.

    Skips the entire session if the API (or its dependencies) is not healthy.
    """
    c = ProfilerClient()
    try:
        health = c.health()
    except requests.RequestException as exc:
        pytest.skip(f"Profiler API not reachable at {config.BASE_URL}: {exc}")

    if health.get("status") != "healthy":
        pytest.skip(f"Profiler API dependencies are not healthy: {health}")

    return c
