"""Numeric field heuristics used by :class:`dexscraper.scraper.DexScraper`."""

import logging
import math
import struct

from ..models import TokenProfile

# Keep the historical logger name so existing logging config still applies.
logger = logging.getLogger("dexscraper.scraper")


class NumericExtractionMixin:
    """Decode IEEE 754 and uint32 values and classify them as market fields."""

    debug: bool
    value_ranges: dict[str, tuple[float, float]]

    def _extract_validated_token_record(
        self, token_name: str, record_data: bytes, position: int
    ) -> TokenProfile | None:
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
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
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
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
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
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
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

    def _extract_numeric_clusters(self, data: bytes, data_start: int) -> list[dict]:
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
    ) -> list[tuple]:
        """Extract all numeric values from window with validation."""
        values = []

        # Extract doubles (8-byte IEEE 754)
        for i in range(0, len(window) - 8, 4):
            try:
                val = struct.unpack("<d", window[i : i + 8])[0]
                if self._is_valid_numeric_value(val):
                    values.append((base_offset + i, val, "double"))
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
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
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
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
            except (
                ValueError,
                TypeError,
                struct.error,
                IndexError,
                OverflowError,
                UnicodeDecodeError,
                KeyError,
                OSError,
            ):
                continue

        # Sort by position and remove overlaps
        values.sort(key=lambda x: x[0])
        return values

    def _is_valid_numeric_value(self, val: float) -> bool:
        """Validate numeric value using established ranges."""
        return (
            not math.isnan(val)
            and not math.isinf(val)
            and abs(val) > 1e-10
            and abs(val) < 1e12
        )

    def _classify_numeric_values(
        self, values: list[tuple[int, float, str]]
    ) -> dict[str, list[tuple[int, float, str]]]:
        """Classify numeric values by probable field type using validated ranges."""
        classified: dict[str, list[tuple[int, float, str]]] = {
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
