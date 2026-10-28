"""Numeric field heuristics used by :class:`dexscraper.scraper.DexScraper`."""

import logging
import struct

from ..models import TokenProfile

# Keep the historical logger name so existing logging config still applies.
logger = logging.getLogger("dexscraper.scraper")


class NumericExtractionMixin:
    """Decode IEEE 754 and uint32 values and classify them as market fields."""

    debug: bool

    def _extract_validated_token_record(
        self, token_name: str, record_data: bytes, position: int
    ) -> TokenProfile | None:
        """Extract complete token record using exact logic from working deep analyzer."""
        fields = {}

        # Use exact logic from analyze_protocol_deep.py that WORKS
        for offset in range(len(record_data) - 8):
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

        # Also try float extraction (as deep analyzer does)
        for offset in range(len(record_data) - 4):
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

        # CRITICAL: Also extract uint32 integers for transaction counts (as deep analyzer finds)
        for offset in range(len(record_data) - 4):
            val = struct.unpack("<I", record_data[offset : offset + 4])[0]

            # Transaction counts: 1000 to 50000 range (based on deep analyzer findings)
            if 1000 <= val <= 50000 and "txns_24h" not in fields:
                fields["txns_24h"] = val
            # Maker counts: 10 to 1000 range
            elif 10 <= val <= 1000 and "makers" not in fields:
                fields["makers"] = val

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
