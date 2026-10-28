"""Token record assembly used by :class:`dexscraper.scraper.DexScraper`."""

import logging
from typing import Any

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

    def _group_clusters_to_tokens(
        self, clusters: list[dict[str, Any]], metadata: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Group numeric clusters with metadata to form complete token records."""
        token_records: list[dict[str, Any]] = []

        # Sort clusters by field completeness
        clusters.sort(key=lambda c: int(c.get("field_types", 0)), reverse=True)

        for cluster in clusters[:20]:  # Process top 20 clusters
            # Find relevant metadata within reasonable distance
            cluster_start = int(cluster.get("start_pos", 0))
            relevant_metadata: dict[str, list[dict[str, Any]]] = {
                "addresses": [],
                "urls": [],
                "protocols": [],
                "age_indicators": [],
                "tokens": [],
            }

            for addr_info in metadata.get("addresses", []):
                pos = addr_info.get("position")
                if isinstance(pos, int) and abs(pos - cluster_start) <= 1000:
                    relevant_metadata["addresses"].append(addr_info)

            for url_info in metadata.get("urls", []):
                pos = url_info.get("position")
                if isinstance(pos, int) and abs(pos - cluster_start) <= 1000:
                    relevant_metadata["urls"].append(url_info)

            for token_info in metadata.get("tokens", []):
                pos = token_info.get("position")
                if isinstance(pos, int) and abs(pos - cluster_start) <= 1000:
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
        token_records.sort(
            key=lambda r: float(r.get("completeness_score", 0.0)), reverse=True
        )

        return token_records

    def _calculate_completeness_score(
        self, cluster: dict[str, Any], metadata: dict[str, list[dict[str, Any]]]
    ) -> float:
        """Calculate completeness score for a token record."""
        score = 0.0

        # Numeric field completeness (max 60 points)
        field_types_raw = cluster.get("field_types", 0)
        field_types = int(field_types_raw) if isinstance(field_types_raw, int) else 0
        score += min(field_types * 10, 60)

        # Metadata completeness (max 40 points)
        if metadata.get("addresses"):
            score += 10
        if metadata.get("urls"):
            score += 10
        if metadata.get("protocols"):
            score += 10
        if metadata.get("age_indicators"):
            score += 10

        return score / 100.0  # Normalize to 0-1 range

    def _build_token_profile(self, record: dict, index: int) -> TokenProfile:
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
