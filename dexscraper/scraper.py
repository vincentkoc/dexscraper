"""DexScreener WebSocket scraper with validated binary protocol extraction."""

import asyncio
from collections.abc import Callable
import inspect
import json
import logging
import os
import random
import re
import ssl
import time
from typing import Any

import websockets

try:
    from websockets.asyncio.client import ClientConnection as WebSocketConnection
except ImportError:  # pragma: no cover - fallback for older websockets layouts
    WebSocketConnection = Any  # type: ignore[misc,assignment]

from .cloudflare_bypass import CloudflareBypass
from .config import PresetConfigs, ScrapingConfig
from .extraction import RecordAssemblyMixin
from .models import ExtractedTokenBatch, TradingPair

logger = logging.getLogger(__name__)

_CONNECT_SIGNATURE = inspect.signature(websockets.connect)
_CONNECT_SUPPORTS_PROXY = "proxy" in _CONNECT_SIGNATURE.parameters
_CONNECT_HEADERS_PARAM = (
    "additional_headers"
    if "additional_headers" in _CONNECT_SIGNATURE.parameters
    else "extra_headers"
)


class DexScraper(RecordAssemblyMixin):
    """WebSocket scraper using validated binary protocol extraction."""

    def __init__(
        self,
        debug: bool = False,
        rate_limit: float = 4.0,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        use_cloudflare_bypass: bool = False,
        config: ScrapingConfig | None = None,
    ) -> None:
        """Initialize the enhanced scraper.

        Args:
            debug: Enable debug logging
            rate_limit: Maximum requests per second
            max_retries: Maximum connection retry attempts
            backoff_base: Base seconds for exponential backoff
            use_cloudflare_bypass: Use cloudscraper to bypass Cloudflare
            config: Scraping configuration (defaults to trending Solana)
        """
        self.debug = debug
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.use_cloudflare_bypass = use_cloudflare_bypass
        self.config = config or PresetConfigs.trending()

        # Setup logging
        level = logging.DEBUG if debug else logging.ERROR
        logging.basicConfig(
            level=level, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        # Rate limiting
        self._last_request = 0.0
        self._min_interval = 1.0 / rate_limit

        # Connection state
        self._retry_count = 0
        self._headers_rotation = 0

        # Cloudflare bypass
        self.cf_bypass = (
            CloudflareBypass(debug=debug) if use_cloudflare_bypass else None
        )

        # Binary protocol extraction parameters (validated)
        self.tolerance_ranges = {
            "price": 0.02,  # 2% for volatile prices
            "txns": 5,  # ±5 for transaction counts
            "makers": 3,  # ±3 for maker counts
            "volume": 0.05,  # 5% for volume data
            "liquidity": 0.05,  # 5% for liquidity data
            "market_cap": 0.05,  # 5% for market cap data
        }

        # Validated data ranges
        self.value_ranges = {
            "price": (0.000001, 0.1),  # Micro to deci range
            "txns": (10, 50000),  # Transaction counts
            "makers": (10, 15000),  # Maker counts
            "volume": (100000, 10000000),  # Volume in USD
            "liquidity": (10000, 1000000),  # Liquidity in USD
            "market_cap": (100000, 50000000),  # Market cap in USD
        }

        # Protocol patterns
        self.protocol_patterns = {
            "chain": ["solana"],
            "protocols": ["pumpfun", "pumpswap"],
            "age_indicators": ["1h", "24h", "6h", "5m"],
            "tokens": ["SOL", "USD", "USDC"],
        }

        # Regex patterns
        self.address_pattern = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
        self.url_pattern = re.compile(r'https?://[^\s<>"]{2,}')

    def get_cloudflare_runtime_warning(self) -> str | None:
        """Return actionable warning when Cloudflare bypass runs in compatibility mode."""
        if not self.cf_bypass:
            return None
        return self.cf_bypass.get_runtime_warning()

    def _get_headers(self) -> dict[str, str]:
        """Get rotated headers to avoid detection."""
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        ]

        ua = user_agents[self._headers_rotation % len(user_agents)]
        self._headers_rotation += 1

        return {
            "User-Agent": ua,
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Origin": "https://dexscreener.com",
            "Sec-WebSocket-Version": "13",
        }

    async def _rate_limit(self) -> None:
        """Implement rate limiting."""
        now = time.time()
        time_since_last = now - self._last_request
        if time_since_last < self._min_interval:
            await asyncio.sleep(self._min_interval - time_since_last)
        self._last_request = time.time()

    def _get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = self.backoff_base * (2 ** min(self._retry_count, 8))
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)  # nosec B311
        return float(delay + jitter)

    def _resolve_proxy_override(self) -> str | bool | None:
        """Resolve optional proxy override from DEXSCRAPER_PROXY environment variable."""
        raw_value = os.environ.get("DEXSCRAPER_PROXY")
        if raw_value is None:
            return None

        value = raw_value.strip()
        if not value or value.lower() in {"0", "false", "none", "off", "disable"}:
            return False

        if value.lower() in {"auto", "default"}:
            return None

        return value

    async def _connect(self) -> WebSocketConnection | None:
        """Establish WebSocket connection with retry logic."""
        uri = self.config.build_websocket_url()
        logger.debug(f"Connecting to: {uri}")

        ssl_context = ssl.create_default_context()
        # Add ALPN support to match curl behavior - this bypasses Cloudflare detection
        ssl_context.set_alpn_protocols(["http/1.1"])

        for attempt in range(self.max_retries):
            try:
                await self._rate_limit()

                headers = self._get_headers()

                # Use Cloudflare bypass if enabled
                if self.cf_bypass:
                    logger.debug("Using Cloudflare bypass")
                    cf_data = await self.cf_bypass.prepare_websocket_connection(uri)
                    headers = self.cf_bypass.get_enhanced_headers(headers)
                    if cf_data.get("cookie_header"):
                        headers["Cookie"] = cf_data["cookie_header"]
                    if cf_data.get("user_agent"):
                        headers["User-Agent"] = cf_data["user_agent"]

                logger.debug(f"Connection attempt {attempt + 1}/{self.max_retries}")

                # Keep Origin set via dedicated websocket arg to avoid duplicates.
                connect_headers = headers.copy()
                connect_headers.pop("Origin", None)

                connect_kwargs: dict[str, Any] = {
                    _CONNECT_HEADERS_PARAM: connect_headers,
                    "origin": "https://dexscreener.com",
                    "ssl": ssl_context,
                    "max_size": None,
                    "ping_timeout": 30,
                    "ping_interval": 20,
                    "close_timeout": 10,
                }

                proxy_override = self._resolve_proxy_override()
                if proxy_override is not None:
                    if _CONNECT_SUPPORTS_PROXY:
                        connect_kwargs["proxy"] = (
                            None if proxy_override is False else proxy_override
                        )
                    else:
                        logger.warning(
                            "DEXSCRAPER_PROXY set but websockets %s doesn't support"
                            " proxy overrides; ignoring.",
                            websockets.__version__,
                        )

                websocket = await websockets.connect(uri, **connect_kwargs)

                self._retry_count = 0  # Reset on successful connection
                logger.info("WebSocket connection established")
                return websocket

            except Exception as e:  # noqa: BLE001 - retry any connect/handshake failure
                self._retry_count = attempt + 1
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    delay = self._get_backoff_delay()
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)

        return None

    async def extract_token_data(self) -> ExtractedTokenBatch:
        """Extract complete token data using validated binary protocol extraction."""
        logger.debug("Starting comprehensive token extraction...")

        websocket = await self._connect()
        if not websocket:
            logger.error("Failed to establish WebSocket connection")
            return ExtractedTokenBatch()

        try:
            # Handle WebSocket handshake
            handshake = await websocket.recv()
            logger.debug(f"Handshake: {len(handshake)} bytes")

            # Get pairs data message (normalize to bytes for binary protocol parsing)
            pairs_raw = await websocket.recv()
            pairs_message = (
                pairs_raw.encode("utf-8") if isinstance(pairs_raw, str) else pairs_raw
            )
            logger.debug(f"Pairs message: {len(pairs_message)} bytes")

            # Navigate to data section using validated approach
            pairs_pos = pairs_message.find(b"pairs")
            if pairs_pos < 0:
                logger.error("No 'pairs' section found in message")
                return ExtractedTokenBatch()

            data_start = pairs_pos + 20  # Validated offset
            data_section = pairs_message[data_start:]

            logger.debug(
                f"Analyzing {len(data_section)} bytes of binary trading data..."
            )

            # Extract tokens using comprehensive methodology
            tokens = await self._extract_all_tokens(data_section, data_start)

            logger.info(f"Successfully extracted {len(tokens)} complete token profiles")
            return ExtractedTokenBatch(tokens=tokens)

        except Exception as e:  # noqa: BLE001 - preserve stream/extract resilience
            logger.error(f"Error during extraction: {e}")
            return ExtractedTokenBatch()
        finally:
            await websocket.close()

    def extract_token_data_sync(self) -> ExtractedTokenBatch:
        """Synchronously extract a single token batch.

        Raises:
            RuntimeError: If called while an event loop is already running.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.extract_token_data())

        raise RuntimeError(
            "extract_token_data_sync() cannot run inside an active event loop. "
            "Use 'await extract_token_data()' instead."
        )

    # Legacy compatibility methods
    async def get_pairs_once(self) -> list[TradingPair] | None:
        """Get pairs using enhanced extraction, return as legacy format."""
        batch = await self.extract_token_data()
        if batch.tokens:
            return batch.to_trading_pairs()
        return None

    async def stream_pairs(
        self,
        callback: Callable[[list[TradingPair] | ExtractedTokenBatch], None]
        | None = None,
        output_format: str = "json",
        use_enhanced_extraction: bool = True,
    ) -> None:
        """Stream trading pairs with enhanced extraction capability."""
        while True:
            try:
                if use_enhanced_extraction:
                    batch = await self.extract_token_data()
                    if batch.tokens:
                        if callback:
                            callback(batch)
                        else:
                            await self._output_enhanced_batch(batch, output_format)
                else:
                    pairs = await self.get_pairs_once()
                    if pairs:
                        if callback:
                            callback(pairs)
                        else:
                            await self._output_pairs(pairs, output_format)

                await asyncio.sleep(5)  # Wait between extractions

            except KeyboardInterrupt:
                logger.info("Streaming stopped by user")
                break
            except Exception as e:  # noqa: BLE001 - preserve stream/extract resilience
                logger.error(f"Error in streaming: {e}")
                await asyncio.sleep(10)

    async def _output_enhanced_batch(
        self, batch: ExtractedTokenBatch, format_type: str
    ) -> None:
        """Output enhanced token batch in specified format."""
        if format_type == "json":
            output = {
                "type": "enhanced_tokens",
                "total_extracted": batch.total_extracted,
                "high_confidence_count": batch.high_confidence_count,
                "tokens": [
                    token.to_output_dict() for token in batch.get_top_tokens(10)
                ],
                "timestamp": batch.extraction_timestamp,
            }
            print(json.dumps(output, separators=(",", ":"), default=str))

        elif format_type == "ohlc":
            ohlc_data = batch.to_ohlc_batch()
            for ohlc in ohlc_data[:10]:  # Top 10
                print(
                    f"TOKEN,{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},{ohlc.close},{ohlc.volume}"
                )

        elif format_type == "mt5":
            ohlc_data = batch.to_ohlc_batch()
            for ohlc in ohlc_data[:10]:  # Top 10
                print(ohlc.to_mt5_format())

    async def _output_pairs(self, pairs: list[TradingPair], format_type: str) -> None:
        """Output pairs in specified format (legacy)."""
        if format_type == "json":
            output = {
                "type": "pairs",
                "pairs": [pair.to_dict() for pair in pairs],
                "timestamp": int(time.time()),
            }
            print(json.dumps(output, separators=(",", ":")))

        elif format_type == "ohlc":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(
                        f"{pair.base_token_symbol},{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},{ohlc.close},{ohlc.volume}"
                    )

        elif format_type == "mt5":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(ohlc.to_mt5_format())

    async def run(
        self, output_format: str = "json", use_enhanced_extraction: bool = True
    ) -> None:
        """Run the enhanced scraper."""
        logger.info("Starting Enhanced DexScreener scraper...")
        try:
            await self.stream_pairs(
                output_format=output_format,
                use_enhanced_extraction=use_enhanced_extraction,
            )
        except KeyboardInterrupt:
            logger.info("Enhanced scraper stopped by user")
        except Exception as e:  # noqa: BLE001 - preserve stream/extract resilience
            logger.error(f"Enhanced scraper error: {e}")
