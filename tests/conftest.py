#!/usr/bin/env python3
"""Pytest configuration and fixtures for dexscraper tests."""

import asyncio
import os
from collections.abc import Generator

import pytest

_LIVE_ENV_VALUES = {"1", "true", "yes", "on"}


def _live_network_enabled() -> bool:
    return os.environ.get("DEXSCRAPER_LIVE", "").strip().lower() in _LIVE_ENV_VALUES


def pytest_configure(config: pytest.Config) -> None:
    """Register markers used by this suite (also declared in pyproject.toml)."""
    config.addinivalue_line(
        "markers",
        "integration: live network tests; require DEXSCRAPER_LIVE=1",
    )
    config.addinivalue_line(
        "markers",
        "live: alias for integration; require DEXSCRAPER_LIVE=1",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip live/integration WebSocket tests unless DEXSCRAPER_LIVE is set."""
    if _live_network_enabled():
        return
    skip_live = pytest.mark.skip(
        reason="live network tests require DEXSCRAPER_LIVE=1"
    )
    for item in items:
        if "integration" in item.keywords or "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_token_data():
    """Sample token data for testing."""
    return {
        "symbol": "TEST",
        "price": 0.000123,
        "volume_24h": 1000000.50,
        "txns_24h": 500,
        "makers": 25,
        "liquidity": 50000.0,
        "market_cap": 5000000.0,
        "confidence_score": 0.85,
        "field_count": 8,
    }


@pytest.fixture
def sample_ohlc_data():
    """Sample OHLC data for testing."""
    return {
        "timestamp": 1756793176,
        "open": 0.000123,
        "high": 0.000127,
        "low": 0.000119,
        "close": 0.000125,
        "volume": 1000000.50,
        "trades": 150,
    }
