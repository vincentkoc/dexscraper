#!/usr/bin/env python3
"""Pytest configuration and fixtures for dexscraper tests."""

import asyncio
from typing import Generator

import pytest


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
