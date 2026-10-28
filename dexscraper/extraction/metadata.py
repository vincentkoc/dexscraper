"""Address, URL and protocol heuristics used by :class:`dexscraper.scraper.DexScraper`."""

import re
from typing import Any

from ..models import TokenProfile
from .symbols import SymbolExtractionMixin

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_ALPHABET_SET = set(_BASE58_ALPHABET)


class MetadataExtractionMixin(SymbolExtractionMixin):
    """Extract addresses, URLs, protocols and age markers near token records."""

    protocol_patterns: dict[str, list[str]]
    address_pattern: re.Pattern[str]
    url_pattern: re.Pattern[str]

    def _enrich_token_profile(
        self,
        profile: TokenProfile,
        token_name: str,
        token_position: int,
        metadata: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Populate metadata fields for a token extracted from numeric records."""
        profile.token_name = profile.token_name or token_name
        profile.chain = profile.chain or self.protocol_patterns["chain"][0]
        profile.protocol = profile.protocol or "unknown"

        max_distance = 1000

        nearby_addresses = sorted(
            [
                address
                for address in metadata.get("addresses", [])
                if isinstance(address.get("position"), int)
                and abs(int(address["position"]) - token_position) <= max_distance
            ],
            key=lambda entry: abs(int(entry["position"]) - token_position),
        )

        for address_info in nearby_addresses:
            address = address_info.get("address")
            if not isinstance(address, str):
                continue
            if not self._is_probable_solana_address(address):
                continue

            address_type = str(address_info.get("type", ""))
            if address_type == "SOL_token":
                profile.quote_address = profile.quote_address or address
                continue

            if address in {
                profile.token_address,
                profile.pair_address,
                profile.creator_address,
                profile.quote_address,
            }:
                continue

            if not profile.token_address:
                profile.token_address = address
            elif not profile.pair_address:
                profile.pair_address = address
            elif not profile.creator_address:
                profile.creator_address = address

        nearby_urls = sorted(
            [
                url
                for url in metadata.get("urls", [])
                if isinstance(url.get("position"), int)
                and abs(int(url["position"]) - token_position) <= max_distance
            ],
            key=lambda entry: abs(int(entry["position"]) - token_position),
        )

        for url_info in nearby_urls:
            url = url_info.get("url")
            if not isinstance(url, str):
                continue
            url_type = str(url_info.get("type", ""))
            if url_type == "twitter" and not profile.twitter:
                profile.twitter = url
            elif url_type == "telegram" and not profile.telegram:
                profile.telegram = url
            elif url_type == "website" and not profile.website:
                profile.website = url

        protocol_candidates = []
        for protocol_info in metadata.get("protocols", []):
            protocol = protocol_info.get("protocol")
            position = protocol_info.get("position")
            if (
                isinstance(protocol, str)
                and isinstance(position, int)
                and abs(position - token_position) <= max_distance
            ):
                protocol_candidates.append((abs(position - token_position), protocol))

        if protocol_candidates:
            protocol_candidates.sort(key=lambda item: item[0])
            nearest_protocol_distance, nearest_protocol = protocol_candidates[0]
            if nearest_protocol_distance <= 220:
                profile.protocol = nearest_protocol

        age_candidates = []
        for age_info in metadata.get("age_indicators", []):
            age = age_info.get("age")
            position = age_info.get("position")
            if (
                isinstance(age, str)
                and isinstance(position, int)
                and abs(position - token_position) <= max_distance
            ):
                age_candidates.append((abs(position - token_position), age))

        if age_candidates:
            age_candidates.sort(key=lambda item: item[0])
            nearest_age_distance, nearest_age = age_candidates[0]
            if nearest_age_distance <= 180:
                profile.age = nearest_age

    def _extract_metadata_patterns(
        self, data: bytes, data_start: int
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract metadata patterns (addresses, URLs, protocols)."""
        # Convert to text for pattern matching
        printable_text = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

        metadata: dict[str, list[dict[str, Any]]] = {
            "addresses": [],
            "urls": [],
            "protocols": [],
            "tokens": [],
            "age_indicators": [],
        }

        # Extract Solana addresses
        addresses = self.address_pattern.findall(printable_text)
        seen_entries: set[tuple[str, int]] = set()
        for addr in addresses:
            if not self._is_probable_solana_address(addr):
                continue

            start = 0
            while True:
                pos = printable_text.find(addr, start)
                if pos < 0:
                    break
                key = (addr, pos)
                if key not in seen_entries:
                    seen_entries.add(key)
                    metadata["addresses"].append(
                        {
                            "address": addr,
                            "position": data_start + pos,
                            "type": self._classify_address(addr),
                        }
                    )
                start = pos + 1

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
            start = 0
            while True:
                pos = printable_text.lower().find(protocol.lower(), start)
                if pos == -1:
                    break
                metadata["protocols"].append(
                    {"protocol": protocol, "position": data_start + pos}
                )
                start = pos + 1
                if len(metadata["protocols"]) >= 100:
                    break

        # Extract age indicators (e.g. 5m, 1h, 6h, 24h)
        for indicator in self.protocol_patterns["age_indicators"]:
            start = 0
            while True:
                pos = printable_text.lower().find(indicator.lower(), start)
                if pos == -1:
                    break
                metadata["age_indicators"].append(
                    {"age": indicator, "position": data_start + pos}
                )
                start = pos + 1
                if len(metadata["age_indicators"]) >= 100:
                    break

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

    def _is_probable_solana_address(self, address: str) -> bool:
        """Validate Solana base58 address by decoding into 32 bytes."""
        if len(address) < 32 or len(address) > 44:
            return False
        if any(char not in _BASE58_ALPHABET_SET for char in address):
            return False

        decoded_value = 0
        for char in address:
            decoded_value = (decoded_value * 58) + _BASE58_ALPHABET.index(char)

        decoded = (
            b""
            if decoded_value == 0
            else decoded_value.to_bytes(
                (decoded_value.bit_length() + 7) // 8, byteorder="big"
            )
        )

        leading_zeros = len(address) - len(address.lstrip("1"))
        decoded = (b"\x00" * leading_zeros) + decoded
        return len(decoded) == 32

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
