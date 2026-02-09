"""Cloudflare bypass utilities using cloudscraper."""

import asyncio
import logging
import time
from typing import Any, Optional

import cloudscraper

logger = logging.getLogger(__name__)


class CloudflareBypass:
    """Handle Cloudflare protection bypass for WebSocket connections."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.scraper = self._create_scraper()
        self._session_cookies: dict[str, str] = {}
        self._last_session_update: float = 0.0
        self._session_ttl = 300  # 5 minutes

    def _create_scraper(self) -> Any:
        """Create a new cloudscraper session."""
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

    def _refresh_session(self) -> None:
        """Reset cookies and rotate to a fresh scraper session."""
        self._session_cookies = {}
        self._last_session_update = 0.0
        try:
            self.scraper.cookies.clear()
        except Exception:
            # Cookie jar type can vary; best effort only.
            pass
        self.scraper = self._create_scraper()

    async def _fetch_main_site(self, main_site_url: str) -> Optional[Any]:
        """Run the blocking cloudscraper request in an executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._make_request, main_site_url)

    def _store_session_cookies(self) -> dict[str, str]:
        """Persist latest cookies from scraper state."""
        self._session_cookies = dict(self.scraper.cookies)
        self._last_session_update = time.time()
        logger.debug("Got %d cookies", len(self._session_cookies))
        return self._session_cookies

    async def get_session_cookies(self, target_url: str) -> dict[str, str]:
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

            logger.debug("Getting session from %s", main_site_url)

            # Make a request to the main site to get past Cloudflare
            response = await self._fetch_main_site(main_site_url)
            status_code: Optional[int] = (
                response.status_code if response is not None else None
            )

            if status_code == 200:
                return self._store_session_cookies()

            if status_code == 403:
                logger.warning(
                    "Cloudflare returned 403, refreshing session and retrying"
                )
            else:
                logger.warning(
                    "Failed to get session: HTTP %s; refreshing session and retrying",
                    status_code,
                )

            self._refresh_session()
            retry_response = await self._fetch_main_site(main_site_url)
            retry_status = retry_response.status_code if retry_response else None
            if retry_status == 200:
                return self._store_session_cookies()

            logger.warning("Retry failed to get session: HTTP %s", retry_status)
        except Exception as e:
            logger.error("Error getting session cookies: %s", e)

        return {}

    def _make_request(self, url: str) -> Optional[Any]:
        """Make synchronous request using cloudscraper."""
        try:
            response = self.scraper.get(url, timeout=30)
            return response
        except Exception as e:
            logger.debug("Request failed: %s", e)
            return None

    def get_enhanced_headers(self, base_headers: dict[str, str]) -> dict[str, str]:
        """Enhance headers with Cloudflare-friendly values."""
        # Just return the base headers as they're already properly configured
        return base_headers.copy()

    async def prepare_websocket_connection(self, websocket_url: str) -> dict[str, Any]:
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
