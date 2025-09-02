"""DexScreener WebSocket scraper with validated binary protocol extraction."""

import asyncio
import json
import logging
import random
import re
import ssl
import struct
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import websockets

from .cloudflare_bypass import CloudflareBypass
from .config import Chain, PresetConfigs, RankBy, ScrapingConfig, Timeframe
from .models import ExtractedTokenBatch, OHLCData, TokenProfile, TradingPair

logger = logging.getLogger(__name__)


class DexScraper:
    """WebSocket scraper using validated binary protocol extraction."""

    def __init__(
        self,
        debug: bool = False,
        rate_limit: float = 4.0,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        use_cloudflare_bypass: bool = False,
        config: Optional[ScrapingConfig] = None,
    ):
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

    def _get_headers(self) -> Dict[str, str]:
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
            "Sec-WebSocket-Version": "13",
            "Origin": "https://dexscreener.com",
            "Sec-WebSocket-Extensions": "permessage-deflate",
            "Connection": "keep-alive, Upgrade",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "websocket",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Upgrade": "websocket",
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
        jitter = delay * 0.25 * (2 * random.random() - 1)  # nosec B311
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
                    if cf_data.get("cookie_header"):
                        headers["Cookie"] = cf_data["cookie_header"]
                    if cf_data.get("user_agent"):
                        headers["User-Agent"] = cf_data["user_agent"]

                logger.debug(f"Connection attempt {attempt + 1}/{self.max_retries}")

                websocket = await websockets.connect(
                    uri,
                    extra_headers=headers,
                    ssl=ssl_context,
                    max_size=None,
                    ping_timeout=30,
                    ping_interval=20,
                    close_timeout=10,
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

            # Get pairs data message
            pairs_message = await websocket.recv()
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

        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            return ExtractedTokenBatch()
        finally:
            await websocket.close()

    async def _extract_all_tokens(
        self, data: bytes, data_start: int
    ) -> List[TokenProfile]:
        """Extract tokens using proven deep analysis methodology from ANALYSIS.md."""
        logger.debug(
            "Using validated deep analysis approach from analyze_protocol_deep.py..."
        )

        # Convert to printable text for symbol extraction
        printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

        # Extract token names using proven patterns (from deep analyzer)
        token_names = self._extract_real_token_names(printable, data_start)
        logger.debug(f"Found {len(token_names)} potential token symbols")

        # Extract complete token records around each symbol
        tokens = []
        positions = sorted(token_names.keys())

        for pos in positions:
            token_name = token_names[pos]
            # Extract record data around this token (±500 bytes as per ANALYSIS.md)
            record_start = max(0, pos - data_start - 500)
            record_end = min(len(data), pos - data_start + 500)
            record_data = data[record_start:record_end]

            # Extract numeric fields using validated IEEE 754 structure
            token_record = self._extract_validated_token_record(
                token_name, record_data, pos
            )
            if token_record:
                tokens.append(token_record)

        logger.info(f"Extracted {len(tokens)} tokens using proven deep analysis method")
        return tokens

    def _extract_real_token_names(
        self, printable: str, data_start: int
    ) -> Dict[int, str]:
        """Extract real token symbols using proven deep analysis patterns."""
        token_names = {}

        # Proven patterns from analyze_protocol_deep.py
        patterns = [
            r'"symbol"\s*:\s*"([^"]+)"',  # JSON-like
            r"symbol\s*:\s*([A-Z0-9]{2,10})",  # Simple format
            r"\$([A-Z]{2,10})\b",  # Dollar prefix
            r'"name"\s*:\s*"([^"]+)"',  # Token name
            r"token\s*:\s*([A-Z0-9]{2,10})",  # Token field
        ]

        all_symbols = []
        for pattern in patterns:
            matches = re.findall(pattern, printable, re.IGNORECASE)
            for match in matches:
                if match and len(match) >= 2:
                    all_symbols.append(match)

        # Look for uppercase sequences that could be tokens
        uppercase_pattern = r"\b([A-Z]{2,10})\b"
        uppercase_matches = re.findall(uppercase_pattern, printable)

        # Validated blacklist from deep analysis
        blacklist = {
            "HTTP",
            "HTTPS",
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "JSON",
            "XML",
            "HTML",
            "CSS",
            "JS",
            "API",
            "URL",
            "URI",
            "TCP",
            "UDP",
            "DNS",
            "SSL",
            "TLS",
            "UTF",
            "ASCII",
            "BASE",
            "TRUE",
            "FALSE",
            "NULL",
            "VOID",
            "INT",
            "FLOAT",
            "DOUBLE",
        }

        for match in uppercase_matches:
            if match not in blacklist:
                all_symbols.append(match)

        # Look for mixed-case token names
        mixed_pattern = r"\b([A-Z][a-z]{2,15})\b"
        mixed_matches = re.findall(mixed_pattern, printable)

        # Filter out common English words
        english_words = {
            "The",
            "And",
            "For",
            "Are",
            "But",
            "Not",
            "You",
            "All",
            "Can",
            "Had",
            "Her",
            "Was",
            "One",
            "Our",
            "Out",
            "Day",
            "Get",
            "Has",
            "Him",
            "His",
            "How",
            "Its",
            "May",
            "New",
            "Now",
            "Old",
            "See",
            "Two",
            "Way",
            "Who",
            "Boy",
            "Did",
            "Http",
            "Https",
            "Json",
            "Server",
            "Client",
            "Request",
            "Response",
            "Error",
            "Success",
            "Failed",
            "Retry",
        }

        for match in mixed_matches:
            if match not in english_words:
                all_symbols.append(match)

        # Remove duplicates and sort by frequency
        symbol_counts = {}
        for symbol in all_symbols:
            symbol_upper = symbol.upper()
            symbol_counts[symbol_upper] = symbol_counts.get(symbol_upper, 0) + 1

        # Sort by frequency (most frequent = most likely real token)
        sorted_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)

        logger.debug(f"Found {len(sorted_symbols)} unique potential token symbols")
        for symbol, count in sorted_symbols[:20]:  # Top 20 most frequent
            pos = printable.find(symbol)
            if pos >= 0:
                token_names[data_start + pos] = symbol

        return token_names

    def _extract_validated_token_record(
        self, token_name: str, record_data: bytes, position: int
    ) -> Optional[TokenProfile]:
        """Extract complete token record using exact logic from working deep analyzer."""
        fields = {}

        # Use exact logic from analyze_protocol_deep.py that WORKS
        for offset in range(len(record_data) - 8):
            try:
                # Extract double (primary format per ANALYSIS.md)
                val = struct.unpack("<d", record_data[offset : offset + 8])[0]

                # Use exact classification from working deep analyzer
                if 0.000001 <= val <= 0.1:  # Price range
                    if "price" not in fields:
                        fields["price"] = val
                elif 1000 <= val <= 10000000:  # Volume/liquidity/mcap
                    if val >= 1000000 and "market_cap" not in fields:
                        fields["market_cap"] = val
                    elif val >= 100000 and "volume_24h" not in fields:
                        fields["volume_24h"] = val
                    elif "liquidity" not in fields:
                        fields["liquidity"] = val
                elif 10 <= val <= 50000:  # Txns/makers - use deep analyzer logic
                    if val >= 1000 and "txns_24h" not in fields:
                        fields["txns_24h"] = int(val)
                    elif "makers" not in fields:
                        fields["makers"] = int(val)
            except:  # nosec B112
                continue

        # Also try float extraction (as deep analyzer does)
        for offset in range(len(record_data) - 4):
            try:
                val = struct.unpack("<f", record_data[offset : offset + 4])[0]

                if 0.000001 <= val <= 0.1:  # Price range
                    if "price" not in fields:
                        fields["price"] = val
                elif 1000 <= val <= 10000000:  # Volume/liquidity/mcap
                    if val >= 1000000 and "market_cap" not in fields:
                        fields["market_cap"] = val
                    elif val >= 100000 and "volume_24h" not in fields:
                        fields["volume_24h"] = val
                    elif "liquidity" not in fields:
                        fields["liquidity"] = val
                elif 10 <= val <= 50000:  # Txns/makers
                    if val >= 1000 and "txns_24h" not in fields:
                        fields["txns_24h"] = int(val)
                    elif "makers" not in fields:
                        fields["makers"] = int(val)
            except:  # nosec B112
                continue

        # CRITICAL: Also extract uint32 integers for transaction counts (as deep analyzer finds)
        for offset in range(len(record_data) - 4):
            try:
                val = struct.unpack("<I", record_data[offset : offset + 4])[0]

                # Transaction counts: 1000 to 50000 range (based on deep analyzer findings)
                if 1000 <= val <= 50000 and "txns_24h" not in fields:
                    fields["txns_24h"] = val
                # Maker counts: 10 to 1000 range
                elif 10 <= val <= 1000 and "makers" not in fields:
                    fields["makers"] = val
            except:  # nosec B112
                continue

        # Return token with at least 3 fields (as deep analyzer does)
        if len(fields) >= 3:
            if self.debug:
                logger.debug(
                    f"✅ Complete record for {token_name} with {len(fields)} fields: {list(fields.keys())}"
                )

            return TokenProfile(
                symbol=token_name,
                price=fields.get("price"),
                volume_24h=fields.get("volume_24h"),
                txns_24h=fields.get("txns_24h"),
                makers=fields.get("makers"),
                liquidity=fields.get("liquidity"),
                market_cap=fields.get("market_cap"),
                confidence_score=min(0.7 + (len(fields) * 0.05), 0.95),
                field_count=len(fields),
            )

        return None

    def _extract_numeric_clusters(self, data: bytes, data_start: int) -> List[Dict]:
        """Extract numeric clusters using validated methodology."""
        clusters = []
        window_size = 500  # Validated window size
        step_size = 200  # Overlapping windows for complete coverage

        for offset in range(0, len(data) - window_size, step_size):
            window = data[offset : offset + window_size]
            numeric_values = self._extract_numerics_from_window(
                window, data_start + offset
            )

            if len(numeric_values) >= 5:  # Minimum fields for a cluster
                # Classify values by type
                classified = self._classify_numeric_values(numeric_values)

                # Require at least 3 different field types
                field_types = len([k for k, v in classified.items() if v])
                if field_types >= 3:
                    clusters.append(
                        {
                            "start_pos": data_start + offset,
                            "end_pos": data_start + offset + window_size,
                            "values": numeric_values,
                            "classified": classified,
                            "field_types": field_types,
                        }
                    )

        return clusters

    def _extract_numerics_from_window(
        self, window: bytes, base_offset: int
    ) -> List[Tuple]:
        """Extract all numeric values from window with validation."""
        values = []

        # Extract doubles (8-byte IEEE 754)
        for i in range(0, len(window) - 8, 4):
            try:
                val = struct.unpack("<d", window[i : i + 8])[0]
                if self._is_valid_numeric_value(val):
                    values.append((base_offset + i, val, "double"))
            except:  # nosec B112
                continue

        # Extract floats (4-byte IEEE 754)
        for i in range(0, len(window) - 4, 2):
            # Skip positions covered by doubles
            if any(abs((base_offset + i) - pos) < 4 for pos, _, _ in values):
                continue

            try:
                val = struct.unpack("<f", window[i : i + 4])[0]
                if self._is_valid_numeric_value(val):
                    values.append((base_offset + i, val, "float"))
            except:  # nosec B112
                continue

        # Extract 32-bit integers (counts)
        for i in range(0, len(window) - 4, 4):
            # Skip positions covered by other types
            if any(abs((base_offset + i) - pos) < 4 for pos, _, _ in values):
                continue

            try:
                val = struct.unpack("<I", window[i : i + 4])[0]
                if (
                    self.value_ranges["txns"][0]
                    <= val
                    <= self.value_ranges["makers"][1]
                ):
                    values.append((base_offset + i, float(val), "uint32"))
            except:  # nosec B112
                continue

        # Sort by position and remove overlaps
        values.sort(key=lambda x: x[0])
        return values

    def _is_valid_numeric_value(self, val: float) -> bool:
        """Validate numeric value using established ranges."""
        return (
            not (val != val)
            and val != float("inf")  # Not NaN
            and val != float("-inf")  # Not infinity
            and abs(val) > 1e-10  # Not negative infinity
            and abs(val) < 1e12  # Not too close to zero  # Not absurdly large
        )

    def _classify_numeric_values(self, values: List[Tuple]) -> Dict[str, List[Tuple]]:
        """Classify numeric values by probable field type using validated ranges."""
        classified = {
            "prices": [],
            "txns": [],
            "makers": [],
            "volumes": [],
            "liquidity": [],
            "market_caps": [],
            "percentages": [],
        }

        for pos, val, dtype in values:
            # Price classification (small decimals)
            if self.value_ranges["price"][0] <= val <= self.value_ranges["price"][1]:
                classified["prices"].append((pos, val, dtype))

            # Transaction count classification
            elif (
                dtype == "uint32"
                and self.value_ranges["txns"][0] <= val <= self.value_ranges["txns"][1]
            ):
                classified["txns"].append((pos, val, dtype))

            # Maker count classification (usually smaller than txns)
            elif (
                dtype in ["uint32", "float"]
                and self.value_ranges["makers"][0]
                <= val
                <= self.value_ranges["makers"][1]
                and val < 20000
            ):  # Makers typically < 20K
                classified["makers"].append((pos, val, dtype))

            # Volume classification
            elif (
                self.value_ranges["volume"][0] <= val <= self.value_ranges["volume"][1]
            ):
                classified["volumes"].append((pos, val, dtype))

            # Liquidity classification
            elif (
                self.value_ranges["liquidity"][0]
                <= val
                <= self.value_ranges["liquidity"][1]
            ):
                classified["liquidity"].append((pos, val, dtype))

            # Market cap classification
            elif (
                self.value_ranges["market_cap"][0]
                <= val
                <= self.value_ranges["market_cap"][1]
            ):
                classified["market_caps"].append((pos, val, dtype))

            # Percentage changes (-100% to +1000%)
            elif -100 <= val <= 1000 and abs(val) > 0.01:
                classified["percentages"].append((pos, val, dtype))

        return classified

    def _extract_metadata_patterns(self, data: bytes, data_start: int) -> Dict:
        """Extract metadata patterns (addresses, URLs, protocols)."""
        # Convert to text for pattern matching
        printable_text = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

        metadata = {
            "addresses": [],
            "urls": [],
            "protocols": [],
            "tokens": [],
            "age_indicators": [],
        }

        # Extract Solana addresses
        addresses = self.address_pattern.findall(printable_text)
        for addr in addresses:
            if len(addr) >= 32:  # Valid Solana address length
                pos = printable_text.find(addr)
                if pos >= 0:
                    metadata["addresses"].append(
                        {
                            "address": addr,
                            "position": data_start + pos,
                            "type": self._classify_address(addr),
                        }
                    )

        # Extract URLs
        urls = self.url_pattern.findall(printable_text)
        for url in urls:
            pos = printable_text.find(url)
            if pos >= 0:
                metadata["urls"].append(
                    {
                        "url": url,
                        "position": data_start + pos,
                        "type": self._classify_url(url),
                    }
                )

        # Extract protocol indicators
        for protocol in self.protocol_patterns["protocols"]:
            positions = []
            start = 0
            while True:
                pos = printable_text.lower().find(protocol.lower(), start)
                if pos == -1:
                    break
                positions.append(data_start + pos)
                start = pos + 1
                if len(positions) >= 10:
                    break

            if positions:
                metadata["protocols"].append(
                    {"protocol": protocol, "positions": positions}
                )

        # Extract token symbols and names
        token_symbols = self._extract_token_symbols(printable_text, data_start)
        metadata["tokens"].extend(token_symbols)

        return metadata

    def _classify_address(self, address: str) -> str:
        """Classify address type based on known patterns."""
        if address == "So11111111111111111111111111111111111111112":
            return "SOL_token"
        elif len(address) >= 40:
            return "potential_contract"
        else:
            return "unknown"

    def _classify_url(self, url: str) -> str:
        """Classify URL type."""
        url_lower = url.lower()
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif "t.me" in url_lower or "telegram" in url_lower:
            return "telegram"
        elif any(domain in url_lower for domain in [".com", ".io", ".xyz", ".org"]):
            return "website"
        else:
            return "unknown"

    def _extract_token_symbols(self, text: str, data_start: int) -> List[Dict]:
        """Extract potential token symbols and names from binary data."""
        import re

        token_symbols = []
        symbol_counts = {}  # Track frequency of each symbol

        # Pattern 1: Common crypto token patterns (2-10 uppercase letters)
        crypto_pattern = re.compile(r"\b[A-Z]{2,10}\b")
        matches = crypto_pattern.findall(text)

        # Count occurrences of each symbol
        for match in matches:
            symbol_counts[match] = symbol_counts.get(match, 0) + 1

        # Extended blacklist based on deep analysis findings
        blacklist = {
            "HTTP",
            "HTTPS",
            "API",
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "JSON",
            "XML",
            "HTML",
            "CSS",
            "JS",
            "PNG",
            "JPG",
            "GIF",
            "TRUE",
            "FALSE",
            "NULL",
            "VOID",
            "INT",
            "CHAR",
            "BOOL",
            "STRING",
            "AND",
            "OR",
            "NOT",
            "IF",
            "ELSE",
            "FOR",
            "WHILE",
            "DO",
            "RETURN",
            "CONST",
            "VAR",
            "LET",
            "NEW",
            "THIS",
            "SUPER",
            "TRY",
            "CATCH",
            "URL",
            "URI",
            "TCP",
            "UDP",
            "DNS",
            "SSL",
            "TLS",
            "UTF",
            "ASCII",
            "BASE",
            "ERROR",
            "INFO",
            "WARN",
            "DEBUG",
            "TRACE",
        }

        # Whitelist known good token symbols from our analysis
        whitelist = {
            "SOL",
            "USDC",
            "USD",
            "WLFI",
            "COIN",
            "MROCKS",
            "OTC",
            "KAIROS",
            "EMULITES",
            "LYN",
            "FINANCE",
            "SHOT",
            "HOPE",
            "AA",
            "EA",
            "FA",
            "PEPE",
            "DOGE",
            "SHIB",
            "BONK",
        }

        for match, count in symbol_counts.items():
            # Prioritize whitelisted tokens
            if match in whitelist:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "whitelisted",
                            "confidence": 0.95,
                            "frequency": count,
                        }
                    )
            # Skip blacklisted terms
            elif match not in blacklist:
                # Higher confidence for symbols that appear multiple times
                confidence = 0.7 if count == 1 else min(0.7 + (count * 0.05), 0.9)

                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "crypto_symbol",
                            "confidence": confidence,
                            "frequency": count,
                        }
                    )

        # Pattern 2: Look for tokens with $ prefix (like $PEPE, $DOGE)
        dollar_pattern = re.compile(r"\$[A-Z]{2,10}\b")
        dollar_matches = dollar_pattern.findall(text)

        for match in set(dollar_matches):
            symbol = match[1:]  # Remove $ prefix
            pos = text.find(match)
            if pos >= 0:
                token_symbols.append(
                    {
                        "symbol": symbol,
                        "position": data_start + pos,
                        "type": "dollar_prefixed",
                        "confidence": 0.9,
                    }
                )

        # Pattern 3: Look for tokens near "symbol" or "name" keywords
        symbol_context_pattern = re.compile(
            r"(?:symbol|name|token)[:\s]*([A-Za-z0-9]{2,10})", re.IGNORECASE
        )
        context_matches = symbol_context_pattern.findall(text)

        for match in set(context_matches):
            if len(match) >= 2 and match.upper() not in ["SYMBOL", "NAME", "TOKEN"]:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match.upper(),
                            "position": data_start + pos,
                            "type": "context_based",
                            "confidence": 0.8,
                        }
                    )

        # Pattern 4: Mixed case tokens (like "Coiny", "Phantom")
        mixed_case_pattern = re.compile(r"\b[A-Z][a-z]{2,15}\b")
        mixed_matches = mixed_case_pattern.findall(text)

        for match in set(mixed_matches):
            # Filter out common English words
            if match.lower() not in [
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "had",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "its",
                "may",
                "new",
                "now",
                "old",
                "see",
                "two",
                "way",
                "who",
                "boy",
                "did",
                "does",
                "each",
                "find",
                "here",
                "just",
                "like",
                "long",
                "make",
                "many",
                "over",
                "part",
                "some",
                "time",
                "very",
                "what",
                "with",
                "have",
                "from",
                "they",
                "know",
                "want",
                "been",
                "good",
                "much",
                "some",
                "time",
                "very",
                "when",
                "come",
                "could",
                "state",
                "there",
                "think",
                "where",
                "will",
                "would",
                "about",
                "after",
                "again",
                "below",
                "being",
                "both",
                "could",
                "every",
                "first",
                "found",
                "great",
                "group",
                "large",
                "last",
                "left",
                "life",
                "little",
                "never",
                "next",
                "often",
                "other",
                "own",
                "right",
                "small",
                "still",
                "such",
                "take",
                "than",
                "them",
                "well",
                "were",
                "Http",
                "Https",
                "Json",
            ]:
                pos = text.find(match)
                if pos >= 0:
                    token_symbols.append(
                        {
                            "symbol": match,
                            "position": data_start + pos,
                            "type": "mixed_case",
                            "confidence": 0.5,
                        }
                    )

        # Sort by confidence and remove low-quality matches
        token_symbols.sort(key=lambda x: x["confidence"], reverse=True)

        # Return top 20 most confident symbols
        return token_symbols[:20]

    def _extract_best_token_symbol(self, metadata: Dict, index: int) -> str:
        """Extract the best token symbol from metadata, with fallback to placeholder."""
        tokens = metadata.get("tokens", [])

        if not tokens:
            return f"UNKNOWN_{index:02d}"

        # Sort by confidence, frequency, and type preference
        def symbol_score(token_info):
            score = token_info["confidence"]

            # Boost score based on frequency (tokens appearing multiple times are more likely correct)
            frequency = token_info.get("frequency", 1)
            if frequency > 1:
                score += min(frequency * 0.02, 0.2)  # Up to 0.2 bonus for frequency

            # Type-based bonuses
            if token_info["type"] == "whitelisted":
                score += 0.5  # Strong preference for known tokens
            elif token_info["type"] == "dollar_prefixed":
                score += 0.3
            elif token_info["type"] == "context_based":
                score += 0.2
            elif token_info["type"] == "crypto_symbol":
                score += 0.1

            return score

        tokens.sort(key=symbol_score, reverse=True)

        # Filter for quality - skip single letters unless whitelisted
        for token in tokens:
            symbol = token["symbol"]

            # Skip single letters unless they're whitelisted (like "AA", "EA", "FA" from our analysis)
            if len(symbol) == 1 and token["type"] != "whitelisted":
                continue

            # Accept symbols between 2-10 characters that are alphanumeric
            if (
                2 <= len(symbol) <= 10
                and symbol.replace("_", "").replace("-", "").isalnum()
            ):
                return symbol.upper()  # Ensure uppercase for consistency

        # If no good symbol found, use the first one if available
        if tokens:
            return tokens[0]["symbol"].upper()

        # Final fallback
        return f"UNKNOWN_{index:02d}"

    def _group_clusters_to_tokens(
        self, clusters: List[Dict], metadata: Dict
    ) -> List[Dict]:
        """Group numeric clusters with metadata to form complete token records."""
        token_records = []

        # Sort clusters by field completeness
        clusters.sort(key=lambda c: c["field_types"], reverse=True)

        for cluster in clusters[:20]:  # Process top 20 clusters
            # Find relevant metadata within reasonable distance
            cluster_start = cluster["start_pos"]
            relevant_metadata = {
                "addresses": [],
                "urls": [],
                "protocols": [],
                "age_indicators": [],
                "tokens": [],
            }

            for addr_info in metadata["addresses"]:
                if abs(addr_info["position"] - cluster_start) <= 1000:
                    relevant_metadata["addresses"].append(addr_info)

            for url_info in metadata["urls"]:
                if abs(url_info["position"] - cluster_start) <= 1000:
                    relevant_metadata["urls"].append(url_info)

            for token_info in metadata["tokens"]:
                if abs(token_info["position"] - cluster_start) <= 1000:
                    relevant_metadata["tokens"].append(token_info)

            # Create token record
            record = {
                "cluster": cluster,
                "metadata": relevant_metadata,
                "completeness_score": self._calculate_completeness_score(
                    cluster, relevant_metadata
                ),
            }

            token_records.append(record)

        # Sort by completeness score
        token_records.sort(key=lambda r: r["completeness_score"], reverse=True)

        return token_records

    def _calculate_completeness_score(self, cluster: Dict, metadata: Dict) -> float:
        """Calculate completeness score for a token record."""
        score = 0.0

        # Numeric field completeness (max 60 points)
        field_types = cluster["field_types"]
        score += min(field_types * 10, 60)

        # Metadata completeness (max 40 points)
        if metadata["addresses"]:
            score += 10
        if metadata["urls"]:
            score += 10
        if metadata["protocols"]:
            score += 10
        if metadata.get("age_indicators"):
            score += 10

        return score / 100.0  # Normalize to 0-1 range

    def _build_token_profile(self, record: Dict, index: int) -> TokenProfile:
        """Build complete token profile from record data."""
        profile = TokenProfile()

        # Basic identification - extract real token symbol
        profile.symbol = self._extract_best_token_symbol(record["metadata"], index)
        profile.record_position = record["cluster"]["start_pos"]
        profile.record_span = (
            record["cluster"]["end_pos"] - record["cluster"]["start_pos"]
        )

        # Extract numeric fields
        classified = record["cluster"]["classified"]

        # Extract values using prioritization
        if classified["prices"]:
            profile.price = classified["prices"][0][1]

        if classified["txns"]:
            profile.txns_24h = int(max(classified["txns"], key=lambda x: x[1])[1])

        if classified["makers"]:
            profile.makers = int(classified["makers"][0][1])

        if classified["volumes"]:
            profile.volume_24h = max(classified["volumes"], key=lambda x: x[1])[1]

        if classified["liquidity"]:
            profile.liquidity = classified["liquidity"][0][1]

        if classified["market_caps"]:
            profile.market_cap = classified["market_caps"][0][1]

        # Extract percentage changes
        percentages = classified["percentages"]
        if len(percentages) >= 1:
            profile.change_5m = percentages[0][1]
        if len(percentages) >= 2:
            profile.change_1h = percentages[1][1]
        if len(percentages) >= 3:
            profile.change_6h = percentages[2][1]
        if len(percentages) >= 4:
            profile.change_24h = percentages[3][1]

        # Extract metadata
        metadata = record["metadata"]

        # Extract addresses
        for addr_info in metadata["addresses"]:
            addr = addr_info["address"]
            if addr_info["type"] == "SOL_token":
                profile.quote_address = addr
            elif not profile.pair_address:
                profile.pair_address = addr
            elif not profile.creator_address:
                profile.creator_address = addr

        # Extract URLs
        for url_info in metadata["urls"]:
            if url_info["type"] == "twitter" and not profile.twitter:
                profile.twitter = url_info["url"]
            elif url_info["type"] == "website" and not profile.website:
                profile.website = url_info["url"]
            elif url_info["type"] == "telegram" and not profile.telegram:
                profile.telegram = url_info["url"]

        # Extract protocol
        if metadata["protocols"]:
            profile.protocol = metadata["protocols"][0]["protocol"]
            profile.chain = "solana"

        # Calculate final metrics
        fields = [
            profile.price,
            profile.volume_24h,
            profile.txns_24h,
            profile.makers,
            profile.liquidity,
            profile.market_cap,
            profile.pair_address,
            profile.protocol,
            profile.website,
        ]

        profile.field_count = len([f for f in fields if f is not None])
        profile.confidence_score = record["completeness_score"]

        return profile

    # Legacy compatibility methods
    async def get_pairs_once(self) -> Optional[List[TradingPair]]:
        """Get pairs using enhanced extraction, return as legacy format."""
        batch = await self.extract_complete_token_data()
        if batch.tokens:
            return batch.to_trading_pairs()
        return None

    async def stream_pairs(
        self,
        callback: Optional[
            Callable[[Union[List[TradingPair], ExtractedTokenBatch]], None]
        ] = None,
        output_format: str = "json",
        use_enhanced_extraction: bool = True,
    ) -> None:
        """Stream trading pairs with enhanced extraction capability."""
        while True:
            try:
                if use_enhanced_extraction:
                    batch = await self.extract_complete_token_data()
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
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                await asyncio.sleep(10)

    async def _output_enhanced_batch(
        self, batch: ExtractedTokenBatch, format_type: str
    ):
        """Output enhanced token batch in specified format."""
        if format_type == "json":
            output = {
                "type": "enhanced_tokens",
                "total_extracted": batch.total_extracted,
                "high_confidence_count": batch.high_confidence_count,
                "tokens": [token.to_dict() for token in batch.get_top_tokens(10)],
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

    async def _output_pairs(self, pairs: List[TradingPair], format_type: str):
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
    ):
        """Run the enhanced scraper."""
        logger.info("Starting Enhanced DexScreener scraper...")
        try:
            await self.stream_pairs(
                output_format=output_format,
                use_enhanced_extraction=use_enhanced_extraction,
            )
        except KeyboardInterrupt:
            logger.info("Enhanced scraper stopped by user")
        except Exception as e:
            logger.error(f"Enhanced scraper error: {e}")
