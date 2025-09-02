"""Binary protocol decoder for DexScreener WebSocket messages."""

import logging
import struct
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import LiquidityData, PriceData, TradingPair, VolumeData

logger = logging.getLogger(__name__)


def handle_double(value: float) -> float:
    """Handle potential NaN/Inf values."""
    try:
        if not isinstance(value, float) or value != value or abs(value) == float("inf"):
            return 0.0
        return value
    except:
        return 0.0


def clean_string(s: str) -> str:
    """Clean invalid and control characters from strings."""
    try:
        if not s:
            return ""
        # Remove non-printable characters except spaces and tabs
        cleaned = "".join(
            char for char in s if (32 <= ord(char) < 127) or ord(char) == 9
        )

        # Filter out common garbage patterns
        if "@" in cleaned or "\\" in cleaned:
            return cleaned.split("@")[0].split("\\")[0]

        return cleaned.strip()
    except:
        return ""


def decode_metrics(data: bytes, start_pos: int) -> Tuple[Dict[str, float], int]:
    """Decode numeric values from binary data."""
    try:
        if start_pos + 64 > len(data):
            return {}, start_pos

        metrics = {}
        values = struct.unpack("8d", data[start_pos : start_pos + 64])

        # Map metrics with validation
        value_map = {
            "price": values[0],
            "priceUsd": values[1],
            "priceChangeH24": values[2],
            "liquidityUsd": values[3],
            "volumeH24": values[4],
            "fdv": values[5],
            "timestamp": values[6],
        }

        # Validate and clean each value
        for key, value in value_map.items():
            cleaned = handle_double(value)
            if cleaned != 0:
                metrics[key] = cleaned

        return metrics, start_pos + 64

    except Exception as e:
        logger.debug(f"Error decoding metrics: {e}")
        return {}, start_pos


def decode_pair(data: bytes) -> Optional[TradingPair]:
    """Decode a single trading pair from binary data."""
    try:
        # First try the original binary parsing approach
        pos = 0
        pair_data = {}

        # Skip initial null bytes but be more flexible
        while pos < len(data) and pos < 10 and data[pos] in (0x00, 0x0A):
            pos += 1

        # Look for recognizable patterns in the binary data
        # Check if this chunk contains printable text that looks like token data
        printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)
        if "solana" in printable or any(
            proto in printable.lower() for proto in ["pump", "raydium"]
        ):
            # This looks like it contains text data, try text-based parsing
            return decode_pair_from_text(data)

        # Try binary field parsing with better error handling
        fields = [
            "chain",
            "protocol",
            "pairAddress",
            "baseTokenName",
            "baseTokenSymbol",
            "baseTokenAddress",
        ]

        for field_idx, field in enumerate(fields):
            if pos >= len(data):
                break

            str_len = data[pos]
            pos += 1

            # More flexible length validation
            if str_len > min(200, len(data) - pos):
                logger.debug(
                    f"Suspicious length {str_len} for field {field} at pos {pos}"
                )
                # Try to find next reasonable field start
                break

            if str_len == 0:
                continue

            if pos + str_len <= len(data):
                try:
                    value = clean_string(
                        data[pos : pos + str_len].decode("utf-8", errors="ignore")
                    )
                    if value and len(value) >= 2:  # Only accept reasonable values
                        pair_data[field] = value
                except:  # nosec B110
                    pass
            pos += str_len

        # Align to 8-byte boundary for doubles
        pos = (pos + 7) & ~7

        # Read and format metrics
        metrics, pos = decode_metrics(data, pos)

        if not metrics or len(pair_data) < 3:
            return None

        # Create data objects
        price_data = None
        if "price" in metrics and "priceUsd" in metrics:
            price_data = PriceData(
                current=metrics["price"],
                usd=metrics["priceUsd"],
                change_24h=metrics.get("priceChangeH24"),
            )

        liquidity_data = None
        if "liquidityUsd" in metrics:
            liquidity_data = LiquidityData(usd=metrics["liquidityUsd"])

        volume_data = None
        if "volumeH24" in metrics:
            volume_data = VolumeData(h24=metrics["volumeH24"])

        # Handle timestamp
        created_at = None
        created_at_formatted = None
        if "timestamp" in metrics and 0 <= metrics["timestamp"] < 4102444800:
            created_at = int(metrics["timestamp"])
            try:
                created_at_formatted = datetime.fromtimestamp(created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except:
                created_at_formatted = "1970-01-01 00:00:00"

        # Create TradingPair object
        trading_pair = TradingPair(
            chain=pair_data.get("chain", ""),
            protocol=pair_data.get("protocol", ""),
            pair_address=pair_data.get("pairAddress", ""),
            base_token_name=pair_data.get("baseTokenName", ""),
            base_token_symbol=pair_data.get("baseTokenSymbol", ""),
            base_token_address=pair_data.get("baseTokenAddress", ""),
            price_data=price_data,
            liquidity_data=liquidity_data,
            volume_data=volume_data,
            fdv=metrics.get("fdv"),
            created_at=created_at,
            created_at_formatted=created_at_formatted,
        )

        # Validate the pair has meaningful data
        if (
            (price_data and (price_data.current != 0 or price_data.usd != 0))
            or (volume_data and volume_data.h24 != 0)
            or (liquidity_data and liquidity_data.usd != 0)
        ):
            return trading_pair

        return None

    except Exception as e:
        logger.debug(f"Error decoding pair: {e}")
        return None


def decode_pair_from_text(data: bytes) -> Optional[TradingPair]:
    """Decode a trading pair using text-based extraction similar to MostafaRoohy's approach."""
    try:
        # Extract printable text
        printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)
        words = [word.strip() for word in printable.split() if len(word.strip()) >= 2]

        if len(words) < 3:
            return None

        # Initialize fields
        chain = "solana"  # Default for this scraper
        protocol = ""  # nosec B105
        pair_address = ""  # nosec B105
        token_name = ""  # nosec B105
        token_symbol = ""  # nosec B105
        token_address = ""  # nosec B105

        # Extract data using pattern matching
        for word in words:
            word_clean = clean_string(word)
            if not word_clean or len(word_clean) < 2:
                continue

            # Protocol identification
            if any(
                proto in word_clean.lower()
                for proto in ["pumpswap", "raydium", "meteora", "jupiter", "orca"]
            ):
                protocol = word_clean
            # Long addresses (Solana addresses are typically 32-44 chars, base58)
            elif (
                len(word_clean) >= 32
                and len(word_clean) <= 44
                and word_clean.replace("1", "").isalnum()
            ):
                if not token_address:
                    token_address = word_clean
                elif not pair_address:
                    pair_address = word_clean
            # Token symbols (short, often uppercase)
            elif (
                word_clean.isupper()
                and 2 <= len(word_clean) <= 10
                and word_clean.isalpha()
            ):
                if not token_symbol:
                    token_symbol = word_clean
            # Token names (longer descriptive text)
            elif (
                3 <= len(word_clean) <= 50
                and not word_clean.isnumeric()
                and not word_clean.startswith("http")
            ):
                # Prefer longer, more descriptive names
                if not token_name or len(word_clean) > len(token_name):
                    # Avoid obvious non-names
                    if not any(
                        skip in word_clean.lower()
                        for skip in ["twitter", "telegram", "website", "pump", "sol"]
                    ):
                        token_name = word_clean

        # Only create pair if we have some meaningful data
        if token_name or token_symbol or (token_address and len(token_address) >= 32):
            return TradingPair(
                chain=chain,
                protocol=protocol or "unknown",
                pair_address=pair_address,
                base_token_name=token_name,
                base_token_symbol=token_symbol,
                base_token_address=token_address,
            )

        return None

    except Exception as e:
        logger.debug(f"Error in text-based pair decoding: {e}")
        return None


def parse_variable_length(data: bytes) -> List[TradingPair]:
    """Parse trading pairs using variable-length approach based on pattern analysis."""
    pairs = []

    try:
        # Extract printable text to find tokens and addresses
        printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

        # Split into potential records - look for common patterns
        # Based on analysis, "solana" appears to be a common separator/marker
        sections = printable.split("solana")

        logger.debug(f"Found {len(sections)} potential sections split by 'solana'")

        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            if len(section.strip()) < 10:  # Skip very short sections
                continue

            # Extract meaningful data from each section
            words = [word.strip() for word in section.split() if len(word.strip()) >= 3]

            if len(words) < 3:
                continue

            # Try to identify components
            protocol = ""  # nosec B105
            pair_address = ""  # nosec B105
            token_name = ""  # nosec B105
            token_symbol = ""  # nosec B105
            token_address = ""  # nosec B105

            for word in words:
                # Potential protocol names
                if any(
                    proto in word.lower()
                    for proto in ["pump", "raydium", "meteora", "jupiter"]
                ):
                    protocol = word
                # Potential addresses (long alphanumeric strings)
                elif (
                    len(word) >= 32
                    and len(word) <= 44
                    and word.replace("1", "").isalnum()
                ):
                    if not token_address:
                        token_address = word
                    elif not pair_address:
                        pair_address = word
                # Potential token symbols (short uppercase)
                elif word.isupper() and 2 <= len(word) <= 10 and word.isalpha():
                    token_symbol = word
                # Potential token names (mixed case, reasonable length)
                elif 3 <= len(word) <= 50 and not word.isnumeric():
                    if not token_name or len(word) > len(token_name):
                        token_name = word

            # Create a trading pair if we have enough data
            if token_name or token_symbol or token_address:
                pair = TradingPair(
                    chain="solana",
                    protocol=protocol or "unknown",
                    pair_address=pair_address,
                    base_token_name=clean_string(token_name),
                    base_token_symbol=clean_string(token_symbol),
                    base_token_address=clean_string(token_address),
                )
                pairs.append(pair)

                if len(pairs) >= 50:  # Limit to prevent too many results
                    break

    except Exception as e:
        logger.debug(f"Error in variable-length parsing: {e}")

    logger.debug(f"Variable-length parser extracted {len(pairs)} pairs")
    return pairs


def parse_message(message: bytes) -> List[TradingPair]:
    """Parse a complete WebSocket message and extract trading pairs."""
    try:
        # Try enhanced parsing first for real numeric data
        try:
            from .enhanced_protocol import parse_message_enhanced

            pairs = parse_message_enhanced(message)
            if pairs:
                logger.debug(
                    f"Enhanced parser extracted {len(pairs)} pairs with real data"
                )
                return pairs
        except ImportError:
            logger.debug("Enhanced parser not available, using fallback")
        except Exception as e:
            logger.debug(f"Enhanced parser failed: {e}, falling back to basic parsing")

        # Original parsing logic as fallback
        if not message.startswith(b"\x00\n1.3.0\n"):
            return []

        pairs_start = message.find(b"pairs")
        if pairs_start == -1:
            return []

        # Skip past "pairs" (5 bytes) + 4-byte header = 9 bytes total
        pairs = []
        pos = pairs_start + 9

        logger.debug(
            f"Starting pair parsing at position {pos}, message length: {len(message)}"
        )

        # Try different chunk sizes based on analysis
        chunk_sizes = [512, 256, 128]  # Try different sizes

        for chunk_size in chunk_sizes:
            pairs_attempt = []
            pos_attempt = pos

            while pos_attempt < len(message) - chunk_size:
                pair = decode_pair(message[pos_attempt : pos_attempt + chunk_size])
                if pair:
                    pairs_attempt.append(pair)
                pos_attempt += chunk_size

                # Stop if we get too many empty results
                if len(pairs_attempt) == 0 and pos_attempt > pos + (chunk_size * 10):
                    break

            logger.debug(f"Chunk size {chunk_size}: found {len(pairs_attempt)} pairs")

            # Use the chunk size that gives us the most valid pairs
            if len(pairs_attempt) > len(pairs):
                pairs = pairs_attempt

        # If we still don't have good results, try variable-length parsing
        if len(pairs) == 0:
            logger.debug("Trying variable-length parsing")
            pairs = parse_variable_length(message[pos:])

        return pairs

    except Exception as e:
        logger.debug(f"Error parsing message: {e}")
        return []
