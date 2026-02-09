#!/usr/bin/env python3
"""Tests for Cloudflare bypass session handling."""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper.cloudflare_bypass import CloudflareBypass


class TestCloudflareBypass:
    """Test Cloudflare bypass behavior."""

    @pytest.mark.asyncio
    async def test_session_recovery_on_403(self):
        """Should refresh scraper session and retry after a 403."""
        first_scraper = Mock()
        first_scraper.cookies = {"cf_clearance": "old"}
        first_scraper.headers = {"User-Agent": "ua-old"}

        second_scraper = Mock()
        second_scraper.cookies = {"cf_clearance": "new"}
        second_scraper.headers = {"User-Agent": "ua-new"}

        with patch(
            "dexscraper.cloudflare_bypass.cloudscraper.create_scraper",
            side_effect=[first_scraper, second_scraper],
        ) as create_scraper:
            bypass = CloudflareBypass()

            with patch.object(
                bypass,
                "_make_request",
                side_effect=[Mock(status_code=403), Mock(status_code=200)],
            ):
                cookies = await bypass.get_session_cookies("wss://io.dexscreener.com")

        assert create_scraper.call_count == 2
        assert cookies == {"cf_clearance": "new"}
        assert bypass._session_cookies == {"cf_clearance": "new"}

    @pytest.mark.asyncio
    async def test_session_cache_is_reused(self):
        """Should return cached cookies when within TTL."""
        scraper = Mock()
        scraper.cookies = {}
        scraper.headers = {"User-Agent": "ua"}

        with patch(
            "dexscraper.cloudflare_bypass.cloudscraper.create_scraper",
            return_value=scraper,
        ):
            bypass = CloudflareBypass()

        bypass._session_cookies = {"cf_clearance": "cached"}
        bypass._last_session_update = time.time()

        with patch.object(bypass, "_fetch_main_site", new_callable=AsyncMock) as fetch:
            cookies = await bypass.get_session_cookies("wss://io.dexscreener.com")
            fetch.assert_not_called()

        assert cookies == {"cf_clearance": "cached"}

    @pytest.mark.asyncio
    async def test_prepare_websocket_connection_outputs_cookie_header(self):
        """Should expose cookie header and user-agent for websocket setup."""
        scraper = Mock()
        scraper.cookies = {}
        scraper.headers = {"User-Agent": "ua-test"}

        with patch(
            "dexscraper.cloudflare_bypass.cloudscraper.create_scraper",
            return_value=scraper,
        ):
            bypass = CloudflareBypass()

        with patch.object(
            bypass,
            "get_session_cookies",
            new=AsyncMock(return_value={"a": "1", "b": "2"}),
        ):
            data = await bypass.prepare_websocket_connection("wss://io.dexscreener.com")

        assert data["cookies"] == {"a": "1", "b": "2"}
        assert data["user_agent"] == "ua-test"
        assert set(data["cookie_header"].split("; ")) == {"a=1", "b=2"}
