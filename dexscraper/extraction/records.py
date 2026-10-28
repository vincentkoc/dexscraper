"""Token record assembly used by :class:`dexscraper.scraper.DexScraper`."""

import logging

from ..models import TokenProfile
from .metadata import MetadataExtractionMixin
from .numeric import NumericExtractionMixin

# Keep the historical logger name so existing logging config still applies.
logger = logging.getLogger("dexscraper.scraper")


class RecordAssemblyMixin(MetadataExtractionMixin, NumericExtractionMixin):
    """Combine symbol, numeric and metadata heuristics into token profiles."""

    async def _extract_all_tokens(
        self, data: bytes, data_start: int
    ) -> list[TokenProfile]:
        """Extract tokens using proven deep analysis methodology from ANALYSIS.md."""
        logger.debug(
            "Using validated deep analysis approach from analyze_protocol_deep.py..."
        )

        # Convert to printable text for symbol extraction
        printable = "".join(chr(b) if 32 <= b <= 126 else " " for b in data)

        # Extract token names using proven patterns (from deep analyzer)
        token_names = self._extract_real_token_names(printable, data_start)
        logger.debug(f"Found {len(token_names)} potential token symbols")
        metadata = self._extract_metadata_patterns(data, data_start)

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
                self._enrich_token_profile(token_record, token_name, pos, metadata)
                tokens.append(token_record)

        logger.info(f"Extracted {len(tokens)} tokens using proven deep analysis method")
        return tokens
