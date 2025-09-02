"""Cloudflare bypass utilities using cloudscraper."""

import asyncio
import logging
import time
from typing import Any, Dict

import cloudscraper

logger = logging.getLogger(__name__)


class CloudflareBypass:
    """Handle Cloudflare protection bypass for WebSocket connections."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self._session_cookies = {}
        self._last_session_update = 0
        self._session_ttl = 300  # 5 minutes

    async def get_session_cookies(self, target_url: str) -> Dict[str, str]:
        """Get valid session cookies by first visiting the main site."""
        current_time = time.time()

        # Check if we have recent cookies
        if (
            self._session_cookies
            and current_time - self._last_session_update < self._session_ttl
        ):
            return self._session_cookies

        try:
            # Visit the actual dexscreener.com site to get CF cookies
            main_site_url = "https://dexscreener.com"

            logger.debug(f"Getting session from {main_site_url}")

            # Make a request to the main site to get past Cloudflare
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._make_request, main_site_url
            )

            if response and response.status_code == 200:
                self._session_cookies = dict(self.scraper.cookies)
                self._last_session_update = current_time
                logger.debug(f"Got {len(self._session_cookies)} cookies")
                return self._session_cookies
            else:
                logger.warning(
                    f"Failed to get session: HTTP {response.status_code if response else 'None'}"
                )

        except Exception as e:
            logger.error(f"Error getting session cookies: {e}")

        return {}

    def _make_request(self, url: str):
        """Make synchronous request using cloudscraper."""
        try:
            response = self.scraper.get(url, timeout=30)
            return response
        except Exception as e:
            logger.debug(f"Request failed: {e}")
            return None

    def get_enhanced_headers(self, base_headers: Dict[str, str]) -> Dict[str, str]:
        """Enhance headers with Cloudflare-friendly values."""
        # Just return the base headers as they're already properly configured
        return base_headers.copy()

    async def prepare_websocket_connection(self, websocket_url: str) -> Dict[str, Any]:
        """Prepare WebSocket connection with Cloudflare bypass."""
        # Get session cookies first
        cookies = await self.get_session_cookies(websocket_url)

        # Create cookie header
        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])

        return {
            "cookies": cookies,
            "cookie_header": cookie_header,
            "user_agent": self.scraper.headers.get("User-Agent", ""),
        }
