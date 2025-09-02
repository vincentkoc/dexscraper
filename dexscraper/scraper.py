"""Main DexScreener WebSocket scraper with improved connection handling."""

import asyncio
import websockets
import json
import ssl
import logging
import urllib.parse
import time
import random
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

from .models import TradingPair, OHLCData
from .protocol import parse_message
from .cloudflare_bypass import CloudflareBypass
from .config import ScrapingConfig, PresetConfigs, Chain, Timeframe, RankBy

logger = logging.getLogger(__name__)


class DexScraper:
    """WebSocket scraper for DexScreener real-time data with anti-detection features."""

    def __init__(self, 
                 debug: bool = False,
                 rate_limit: float = 4.0,
                 max_retries: int = 5,
                 backoff_base: float = 1.0,
                 use_cloudflare_bypass: bool = False,
                 config: Optional[ScrapingConfig] = None):
        """Initialize the scraper.
        
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
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Rate limiting
        self._last_request = 0.0
        self._min_interval = 1.0 / rate_limit
        
        # Connection state
        self._retry_count = 0
        self._headers_rotation = 0
        
        # Cloudflare bypass
        self.cf_bypass = CloudflareBypass(debug=debug) if use_cloudflare_bypass else None

    def _get_headers(self) -> Dict[str, str]:
        """Get rotated headers to avoid detection."""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0',
        ]
        
        ua = user_agents[self._headers_rotation % len(user_agents)]
        self._headers_rotation += 1
        
        return {
            'User-Agent': ua,
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Sec-WebSocket-Version': '13',
            'Origin': 'https://dexscreener.com',
            'Sec-WebSocket-Extensions': 'permessage-deflate',
            'Connection': 'keep-alive, Upgrade',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'websocket',
            'Sec-Fetch-Site': 'same-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade': 'websocket',
        }

    async def _rate_limit(self):
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
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return delay + jitter

    async def _connect(self) -> Optional[websockets.WebSocketServerProtocol]:
        """Establish WebSocket connection with retry logic."""
        uri = self.config.build_websocket_url()
        logger.debug(f"Connecting to: {uri}")
        
        ssl_context = ssl.create_default_context()
        
        for attempt in range(self.max_retries):
            try:
                await self._rate_limit()
                
                headers = self._get_headers()
                
                # Use Cloudflare bypass if enabled
                if self.cf_bypass:
                    logger.debug("Using Cloudflare bypass")
                    cf_data = await self.cf_bypass.prepare_websocket_connection(uri)
                    headers = self.cf_bypass.get_enhanced_headers(headers)
                    if cf_data.get('cookie_header'):
                        headers['Cookie'] = cf_data['cookie_header']
                    if cf_data.get('user_agent'):
                        headers['User-Agent'] = cf_data['user_agent']
                
                logger.debug(f"Connection attempt {attempt + 1}/{self.max_retries}")
                
                websocket = await websockets.connect(
                    uri,
                    extra_headers=headers,
                    ssl=ssl_context,
                    max_size=None,
                    ping_timeout=30,
                    ping_interval=20,
                    close_timeout=10
                )
                
                self._retry_count = 0  # Reset on successful connection
                logger.info("WebSocket connection established")
                return websocket
                
            except Exception as e:
                self._retry_count = attempt + 1
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self._get_backoff_delay()
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
        
        return None

    async def stream_pairs(self, 
                          callback: Optional[Callable[[List[TradingPair]], None]] = None,
                          output_format: str = "json") -> None:
        """Stream trading pairs with callback or print output.
        
        Args:
            callback: Optional callback function to handle pairs
            output_format: Output format - "json", "ohlc", or "mt5"
        """
        while True:
            websocket = await self._connect()
            if not websocket:
                logger.error("Failed to establish connection after all retries")
                await asyncio.sleep(60)  # Wait longer before retrying connection
                continue
            
            try:
                async for message in websocket:
                    if message == "ping":
                        await websocket.send("pong")
                        continue
                    
                    if isinstance(message, bytes):
                        pairs = parse_message(message)
                        
                        if pairs:
                            if callback:
                                callback(pairs)
                            else:
                                await self._output_pairs(pairs, output_format)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue
            finally:
                if websocket:
                    await websocket.close()

    async def _output_pairs(self, pairs: List[TradingPair], format_type: str):
        """Output pairs in specified format."""
        if format_type == "json":
            output = {
                "type": "pairs",
                "pairs": [pair.to_dict() for pair in pairs],
                "timestamp": int(time.time())
            }
            print(json.dumps(output, separators=(',', ':')))
        
        elif format_type == "ohlc":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(f"{pair.base_token_symbol},{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},{ohlc.close},{ohlc.volume}")
        
        elif format_type == "mt5":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(ohlc.to_mt5_format())

    async def get_pairs_once(self) -> Optional[List[TradingPair]]:
        """Get a single batch of pairs without streaming."""
        websocket = await self._connect()
        if not websocket:
            return None
        
        try:
            # Wait for first message
            timeout = 30
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            
            if isinstance(message, bytes):
                pairs = parse_message(message)
                return pairs
        
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for data")
        except Exception as e:
            logger.error(f"Error getting pairs: {e}")
        finally:
            await websocket.close()
        
        return None

    async def run(self, output_format: str = "json"):
        """Run the scraper indefinitely."""
        logger.info("Starting DexScreener scraper...")
        try:
            await self.stream_pairs(output_format=output_format)
        except KeyboardInterrupt:
            logger.info("Scraper stopped by user")
        except Exception as e:
            logger.error(f"Scraper error: {e}")