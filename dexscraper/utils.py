"""Utility functions for dexscraper package."""

import asyncio
import hashlib
import re
import struct
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


def extract_floats_from_bytes(
    data: bytes, offset: int = 0, count: Optional[int] = None
) -> List[float]:
    """Extract IEEE 754 single-precision floats from binary data.

    Args:
        data: Binary data to extract from
        offset: Starting offset in bytes
        count: Maximum number of floats to extract

    Returns:
        List of extracted float values
    """
    floats = []
    pos = offset

    while pos <= len(data) - 4:  # Need at least 4 bytes for a float
        try:
            value = struct.unpack("<f", data[pos : pos + 4])[0]  # Little-endian

            # Filter out invalid/extreme values
            if is_valid_float(value):
                floats.append(value)

            if count and len(floats) >= count:
                break

        except struct.error:
            pass

        pos += 1  # Move by 1 byte to find unaligned floats

    return floats


def extract_doubles_from_bytes(
    data: bytes, offset: int = 0, count: Optional[int] = None
) -> List[float]:
    """Extract IEEE 754 double-precision floats from binary data.

    Args:
        data: Binary data to extract from
        offset: Starting offset in bytes
        count: Maximum number of doubles to extract

    Returns:
        List of extracted double values
    """
    doubles = []
    pos = offset

    while pos <= len(data) - 8:  # Need at least 8 bytes for a double
        try:
            value = struct.unpack("<d", data[pos : pos + 8])[0]  # Little-endian

            # Filter out invalid/extreme values
            if is_valid_float(value):
                doubles.append(value)

            if count and len(doubles) >= count:
                break

        except struct.error:
            pass

        pos += 1  # Move by 1 byte to find unaligned doubles

    return doubles


def is_valid_float(value: float) -> bool:
    """Check if a float value is valid for trading data.

    Args:
        value: Float value to validate

    Returns:
        True if value appears to be valid trading data
    """
    import math

    # Check for NaN, infinity
    if not math.isfinite(value):
        return False

    # Check for reasonable bounds (crypto prices/volumes)
    if abs(value) < 1e-15 or abs(value) > 1e15:
        return False

    # Check for suspicious patterns (like uninitialized memory)
    if value == 0.0 or abs(value) == 1.0:
        return False

    return True


def extract_solana_addresses(data: bytes) -> List[str]:
    """Extract Solana Base58 addresses from binary data.

    Args:
        data: Binary data to search

    Returns:
        List of found Solana addresses
    """
    # Solana addresses are 32-44 characters, Base58 encoded
    address_pattern = rb"[1-9A-HJ-NP-Za-km-z]{32,44}"

    addresses = []
    for match in re.finditer(address_pattern, data):
        try:
            address = match.group().decode("ascii")
            # Additional validation - Solana addresses typically start with certain chars
            if (
                address[0]
                in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            ):
                addresses.append(address)
        except UnicodeDecodeError:
            continue

    return list(set(addresses))  # Remove duplicates


def extract_urls(data: bytes) -> List[str]:
    """Extract URLs from binary data.

    Args:
        data: Binary data to search

    Returns:
        List of found URLs
    """
    # Common URL patterns in crypto data
    url_patterns = [
        rb"https?://[^\x00\s]+",  # Basic HTTP(S) URLs
        rb"twitter\.com/[^\x00\s]+",  # Twitter URLs
        rb"x\.com/[^\x00\s]+",  # X.com URLs
        rb"t\.me/[^\x00\s]+",  # Telegram URLs
    ]

    urls = []
    for pattern in url_patterns:
        for match in re.finditer(pattern, data, re.IGNORECASE):
            try:
                url = match.group().decode("ascii")
                # Clean up common trailing garbage
                url = clean_url(url)
                if is_valid_url(url):
                    urls.append(url)
            except UnicodeDecodeError:
                continue

    return list(set(urls))  # Remove duplicates


def clean_url(url: str) -> str:
    """Clean extracted URL by removing common trailing garbage.

    Args:
        url: Raw extracted URL

    Returns:
        Cleaned URL
    """
    # Remove common trailing characters that aren't part of URLs
    url = re.sub(r"[^\w\-_.~:/?#[\]@!$&\'()*+,;=%]+$", "", url)

    # Remove null bytes and other control characters
    url = "".join(char for char in url if ord(char) >= 32)

    return url


def is_valid_url(url: str) -> bool:
    """Validate if extracted URL looks legitimate.

    Args:
        url: URL to validate

    Returns:
        True if URL appears valid
    """
    if len(url) < 10 or len(url) > 200:
        return False

    # Must contain valid URL components
    if not any(
        domain in url.lower() for domain in [".com", ".org", ".net", ".io", ".me"]
    ):
        return False

    # Should not contain binary garbage patterns
    if any(char in url for char in "\x00\x01\x02\x03\x04\x05"):
        return False

    return True


def cluster_numeric_values(
    values: List[float], tolerance: float = 0.05
) -> List[List[float]]:
    """Cluster numeric values by proximity.

    Args:
        values: List of numeric values to cluster
        tolerance: Relative tolerance for clustering (0.05 = 5%)

    Returns:
        List of clusters, each containing similar values
    """
    if not values:
        return []

    # Sort values for efficient clustering
    sorted_values = sorted(values)
    clusters = []
    current_cluster = [sorted_values[0]]

    for value in sorted_values[1:]:
        # Check if value is close to the last value in current cluster
        last_value = current_cluster[-1]

        if last_value == 0:
            relative_diff = abs(value)
        else:
            relative_diff = abs(value - last_value) / abs(last_value)

        if relative_diff <= tolerance:
            current_cluster.append(value)
        else:
            # Start new cluster
            if len(current_cluster) >= 2:  # Only keep clusters with multiple values
                clusters.append(current_cluster)
            current_cluster = [value]

    # Add final cluster
    if len(current_cluster) >= 2:
        clusters.append(current_cluster)

    return clusters


def calculate_confidence_score(
    field_count: int, numeric_clusters: int, metadata_count: int
) -> float:
    """Calculate confidence score for a token profile.

    Args:
        field_count: Number of extracted fields
        numeric_clusters: Number of numeric data clusters found
        metadata_count: Number of metadata items (addresses, URLs) found

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Field count contribution (up to 0.5)
    field_score = min(field_count / 10.0, 0.5)

    # Numeric clusters contribution (up to 0.3)
    cluster_score = min(numeric_clusters / 10.0, 0.3)

    # Metadata contribution (up to 0.2)
    metadata_score = min(metadata_count / 5.0, 0.2)

    total_score = field_score + cluster_score + metadata_score

    # Boost for complete profiles
    if field_count >= 5 and numeric_clusters >= 3 and metadata_count >= 1:
        total_score += 0.1  # Completeness bonus

    return min(total_score, 1.0)


def format_timestamp(timestamp: Optional[int] = None) -> str:
    """Format timestamp for display.

    Args:
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = int(time.time())

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_number(value: Optional[float], precision: int = 8) -> str:
    """Format numeric value for display.

    Args:
        value: Numeric value to format
        precision: Decimal precision

    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"

    if abs(value) >= 1:
        return f"{value:,.{precision}f}".rstrip("0").rstrip(".")
    else:
        return f"{value:.{precision}f}".rstrip("0").rstrip(".")


def format_percentage(value: Optional[float]) -> str:
    """Format percentage value for display.

    Args:
        value: Percentage value (0.05 = 5%)

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def format_volume(value: Optional[float]) -> str:
    """Format volume/market cap value for display.

    Args:
        value: Volume value in USD

    Returns:
        Formatted volume string with appropriate units
    """
    if value is None:
        return "N/A"

    if abs(value) >= 1_000_000_000:  # Billions
        return f"${value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:  # Millions
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:  # Thousands
        return f"${value/1_000:.2f}K"
    else:
        return f"${value:.2f}"


def generate_token_id(data: bytes) -> str:
    """Generate unique ID for token data.

    Args:
        data: Binary data to hash

    Returns:
        Short unique identifier
    """
    hash_obj = hashlib.md5(data, usedforsecurity=False)
    return hash_obj.hexdigest()[:8]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, handling zero division.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division by zero

    Returns:
        Division result or default value
    """
    if denominator == 0:
        return default

    return numerator / denominator


def normalize_symbol(symbol: str) -> str:
    """Normalize token symbol for consistency.

    Args:
        symbol: Raw token symbol

    Returns:
        Normalized symbol
    """
    if not symbol:
        return "UNK"

    # Remove non-alphanumeric characters
    normalized = re.sub(r"[^A-Z0-9]", "", symbol.upper())

    # Limit length
    normalized = normalized[:10]

    return normalized or "UNK"


async def with_timeout(coro, timeout_seconds: float):
    """Execute coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds

    Returns:
        Coroutine result

    Raises:
        asyncio.TimeoutError: If operation times out
    """
    return await asyncio.wait_for(coro, timeout=timeout_seconds)


def exponential_backoff(
    attempt: int, base_delay: float = 1.0, max_delay: float = 60.0
) -> float:
    """Calculate exponential backoff delay.

    Args:
        attempt: Attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds
    """
    delay = base_delay * (2 ** min(attempt, 10))  # Cap at 2^10
    return min(delay, max_delay)


def validate_trading_data(price: Optional[float], volume: Optional[float]) -> bool:
    """Validate trading data for reasonableness.

    Args:
        price: Token price
        volume: Trading volume

    Returns:
        True if data appears valid
    """
    # Price validation
    if price is not None:
        if not is_valid_float(price):
            return False
        if price <= 0 or price > 1000000:  # Reasonable price bounds
            return False

    # Volume validation
    if volume is not None:
        if not is_valid_float(volume):
            return False
        if volume < 0 or volume > 1e12:  # Reasonable volume bounds
            return False

    return True


class DataBuffer:
    """Circular buffer for streaming data."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[Any] = []
        self.index = 0

    def append(self, item: Any):
        """Add item to buffer."""
        if len(self.buffer) < self.max_size:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.index = (self.index + 1) % self.max_size

    def get_recent(self, count: int = 10) -> List[Any]:
        """Get most recent items."""
        if len(self.buffer) <= count:
            return self.buffer[:]

        # Handle circular buffer wraparound
        if self.index == 0:
            return self.buffer[-count:]
        else:
            recent = self.buffer[max(0, self.index - count) : self.index]
            if len(recent) < count:
                remaining = count - len(recent)
                recent = self.buffer[-remaining:] + recent
            return recent

    def clear(self):
        """Clear buffer."""
        self.buffer.clear()
        self.index = 0
