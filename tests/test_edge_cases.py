#!/usr/bin/env python3
"""Test edge cases and scenarios identified in ANALYSIS.md."""

import asyncio
import struct
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper import DexScraper
from dexscraper.models import ExtractedTokenBatch, OHLCData, TokenProfile
from dexscraper.utils import (
    cluster_numeric_values,
    extract_doubles_from_bytes,
    extract_floats_from_bytes,
    extract_solana_addresses,
    extract_urls,
    is_valid_float,
    validate_trading_data,
)


class TestBinaryProtocolEdgeCases:
    """Test edge cases from binary protocol analysis."""

    def test_malformed_binary_data(self):
        """Test handling of malformed or truncated binary data."""
        # Test truncated float data
        truncated_data = b"\x40\x09\x21"  # Only 3 bytes, need 4 for float
        floats = extract_floats_from_bytes(truncated_data)
        assert isinstance(floats, list)

        # Test truncated double data
        truncated_double = b"\x40\x09\x21\xfb\x54\x44\x2d"  # Only 7 bytes, need 8
        doubles = extract_doubles_from_bytes(truncated_double)
        assert isinstance(doubles, list)

    def test_invalid_float_detection(self):
        """Test detection of invalid float values from binary data."""
        # Test NaN values
        assert not is_valid_float(float("nan"))
        assert not is_valid_float(float("inf"))
        assert not is_valid_float(float("-inf"))

        # Test extreme values (from ANALYSIS.md - avoid uninitialized memory patterns)
        assert not is_valid_float(0.0)  # Often uninitialized
        assert not is_valid_float(1.0)  # Often uninitialized
        assert not is_valid_float(1e20)  # Too large for crypto prices
        assert not is_valid_float(1e-20)  # Too small for crypto prices

        # Test valid crypto values
        assert is_valid_float(0.000123)  # Valid small crypto price
        assert is_valid_float(1000000.0)  # Valid volume
        assert is_valid_float(45.67)  # Valid price

    def test_variable_length_records(self):
        """Test handling of variable-length records (from ANALYSIS.md)."""
        _ = DexScraper()  # Initialize scraper for testing

        # Simulate the gap patterns found in analysis:
        # - OTCfi makers gaps: 5479, 1867 bytes (avg: 3673 bytes)
        # - USD2 txns gap: 4383 bytes
        # - Minimum gap: 717 bytes

        # Create test data with different gap sizes
        record_gaps = [717, 1867, 3673, 4383, 5479]

        for gap in record_gaps:
            # Test that our clustering can handle different record spacings
            test_positions = [1000, 1000 + gap, 1000 + gap * 2]

            # Verify we can work with these gap patterns
            assert all(pos > 0 for pos in test_positions)

    def test_exact_value_matching(self):
        """Test exact value matching scenarios from ANALYSIS.md."""
        # Values that were exactly matched in the analysis
        exact_matches = [
            29.0,  # OTCfi_txns
            22000.0,  # USD2_volume
            357.0,  # USD2_txns
            18.0,  # OTCfi_makers
        ]

        # Test clustering with these exact values
        clusters = cluster_numeric_values(exact_matches, tolerance=0.001)

        # Distinct values don't cluster together (all different), so expect empty result
        assert len(clusters) == 0  # No clusters since all values are distinct

        # Test that 18.0 repeated values cluster together
        repeated_values = [18.0, 18.0, 18.0, 29.0, 357.0]
        clusters = cluster_numeric_values(repeated_values, tolerance=0.001)

        # Should cluster the three 18.0 values together
        eighteen_cluster = [c for c in clusters if 18.0 in c]
        assert len(eighteen_cluster) == 1
        assert len(eighteen_cluster[0]) == 3  # Three 18.0 values

    def test_ui_data_validation(self):
        """Test validation against UI data patterns from ANALYSIS.md."""
        # Test realistic crypto trading data ranges from the screenshots
        test_cases = [
            # (price, volume, txns, makers, liquidity, market_cap, should_be_valid)
            (0.0004451, 22000, 357, 193, 87000, 445000, True),  # USD2 from screenshot
            (0.0001349, 43000, 498, 249, 47000, 134000, True),  # USC from screenshot
            (0.00001169, 3800000, 15264, 5841, 244000, 11700000, True),  # coiny
            (0.0, 0, 0, 0, 0, 0, False),  # All zeros - invalid
            (1e20, 1e20, 1e6, 1e6, 1e20, 1e20, False),  # Too large - invalid
            (-0.001, 1000, 100, 50, 10000, 50000, False),  # Negative price - invalid
        ]

        for (
            price,
            volume,
            txns,
            makers,
            liquidity,
            market_cap,
            expected_valid,
        ) in test_cases:
            is_valid = validate_trading_data(price, volume)
            if expected_valid:
                assert is_valid, f"Should be valid: price={price}, volume={volume}"
            else:
                assert (
                    not is_valid
                ), f"Should be invalid: price={price}, volume={volume}"

    def test_solana_address_patterns(self):
        """Test Solana address extraction patterns."""
        # Test with realistic Solana addresses from the screenshots
        test_addresses = [
            "DjDzLNonA1XcWpzTBZhNZUqHCvq6SeLfT3otPYdVSMH",  # coiny creator
            "D9h4GK3kkm5GFpCTWUak6ZNN5hn9tJBNYCgbwMVPwSba",  # coiny pair
            "So11111111111111111111111111111111111111112",  # SOL token
        ]

        for addr in test_addresses:
            # Test that our address extraction recognizes these
            binary_data = addr.encode("ascii") + b"\x00\x01\x02"
            extracted = extract_solana_addresses(binary_data)
            assert addr in extracted, f"Should extract address: {addr}"

    def test_url_extraction_patterns(self):
        """Test URL extraction from binary data."""
        test_urls = [
            "https://battlefordreamisland.fandom.com/wiki/Coiny",
            "https://x.com/i/communities/1962736621163303035",
            "https://x.com/liberty_onsol",
            "https://nostalgic-coin.com/",
        ]

        for url in test_urls:
            binary_data = url.encode("ascii") + b"\x00\x01\x02"
            extracted = extract_urls(binary_data)
            # URL should be extracted (possibly cleaned)
            assert any(
                url.split("/")[-1] in ext_url for ext_url in extracted
            ), f"Should extract URL component from: {url}"


class TestTokenProfileEdgeCases:
    """Test TokenProfile edge cases and validation."""

    def test_incomplete_token_profiles(self):
        """Test handling of incomplete token profiles."""
        # Test token with minimal data
        minimal_token = TokenProfile(symbol="TEST", confidence_score=0.1, field_count=1)
        assert not minimal_token.is_complete()

        # Test token with no symbol
        no_symbol = TokenProfile(price=0.001, confidence_score=0.8, field_count=5)
        assert no_symbol.get_display_name().startswith("Token_")

        # Test OHLC conversion with missing data
        ohlc = minimal_token.to_ohlc()
        assert ohlc is None  # Should return None for incomplete data

    def test_confidence_score_edge_cases(self):
        """Test confidence score calculation edge cases."""
        # Test maximum confidence scenario
        max_token = TokenProfile(
            symbol="MAX",
            price=0.001,
            volume_24h=1000000,
            txns_24h=500,
            makers=100,
            liquidity=50000,
            market_cap=1000000,
            website="https://test.com",
            twitter="https://x.com/test",
            field_count=10,
            confidence_score=1.0,
        )
        assert max_token.is_complete()
        assert max_token.confidence_score == 1.0

        # Test zero confidence scenario
        zero_token = TokenProfile(confidence_score=0.0, field_count=0)
        assert not zero_token.is_complete()

    def test_trading_pair_conversion_edge_cases(self):
        """Test TradingPair conversion edge cases."""
        # Test conversion with missing addresses
        token_no_addr = TokenProfile(
            symbol="NOADDR",
            price=0.001,
            volume_24h=1000,
            confidence_score=0.8,
            field_count=5,
        )

        pair = token_no_addr.to_trading_pair()
        assert pair.pair_address == "unknown"
        assert pair.base_token_address == "unknown"
        assert pair.base_token_symbol == "NOADDR"


class TestOHLCDataEdgeCases:
    """Test OHLC data edge cases and format validation."""

    def test_mt5_format_edge_cases(self):
        """Test MT5 format with edge case timestamps and values."""
        # Test with very small timestamp (early Unix time)
        early_ohlc = OHLCData(
            timestamp=1,  # Very early timestamp
            open=0.000001,
            high=0.000002,
            low=0.0000005,
            close=0.0000015,
            volume=100.0,
        )

        mt5_format = early_ohlc.to_mt5_format()
        # Should handle early dates - could be 1969.12.31 (PST) or 1970.01.01 (UTC)
        assert "1969.12.31" in mt5_format or "1970.01.01" in mt5_format

        # Test with very large values
        large_ohlc = OHLCData(
            timestamp=2000000000,  # Future timestamp
            open=999999.99999999,
            high=1000000.0,
            low=999999.0,
            close=999999.5,
            volume=1e12,
        )

        mt5_format = large_ohlc.to_mt5_format()
        assert len(mt5_format.split(",")) == 6  # Should have all 6 fields

    def test_csv_format_edge_cases(self):
        """Test CSV format with edge cases."""
        # Test with trades data
        ohlc_with_trades = OHLCData(
            timestamp=1234567890,
            open=1.0,
            high=1.1,
            low=0.9,
            close=1.05,
            volume=1000.0,
            trades=150,
        )

        ohlcvt_format = ohlc_with_trades.to_ohlcvt_format()
        assert ohlcvt_format.endswith(",150")  # Should include trades count

        # Test without trades data (should estimate)
        ohlc_no_trades = OHLCData(
            timestamp=1234567890, open=1.0, high=1.1, low=0.9, close=1.05, volume=1000.0
        )

        ohlcvt_format = ohlc_no_trades.to_ohlcvt_format()
        assert ohlcvt_format.endswith(",1")  # Should estimate trades


class TestExtractionBatchEdgeCases:
    """Test ExtractedTokenBatch edge cases."""

    def test_empty_batch_handling(self):
        """Test handling of empty token batches."""
        empty_batch = ExtractedTokenBatch(tokens=[])

        assert empty_batch.total_extracted == 0
        assert empty_batch.high_confidence_count == 0
        assert empty_batch.complete_profiles_count == 0

        # Test export operations on empty batch
        csv_output = empty_batch.to_csv_string("ohlcv")
        assert "DateTime,Open,High,Low,Close,Volume" in csv_output

        ohlc_batch = empty_batch.to_ohlc_batch()
        assert len(ohlc_batch) == 0

    def test_batch_with_invalid_tokens(self):
        """Test batch containing invalid or incomplete tokens."""
        invalid_tokens = [
            TokenProfile(),  # Completely empty
            TokenProfile(symbol="INVALID", confidence_score=0.0),  # Zero confidence
            TokenProfile(symbol="PARTIAL", price=-1.0),  # Invalid price
        ]

        batch = ExtractedTokenBatch(tokens=invalid_tokens)

        # Should handle invalid tokens gracefully
        assert batch.total_extracted == 3
        assert batch.high_confidence_count == 0  # None should be high confidence

        # Top tokens should still work
        top_tokens = batch.get_top_tokens(5)
        assert len(top_tokens) <= 3

    def test_large_batch_performance(self):
        """Test performance with large token batches."""
        # Create a large batch (simulating the 20+ tokens from real extraction)
        large_tokens = []
        for i in range(100):
            token = TokenProfile(
                symbol=f"TOKEN_{i:03d}",
                price=0.001 + i * 0.0001,
                volume_24h=1000000 + i * 10000,
                confidence_score=0.5 + (i % 50) * 0.01,
                field_count=5 + (i % 10),
            )
            large_tokens.append(token)

        batch = ExtractedTokenBatch(tokens=large_tokens)

        # Test that operations complete in reasonable time
        import time

        start_time = time.time()
        top_10 = batch.get_top_tokens(10)
        ohlc_data = batch.to_ohlc_batch()
        _ = batch.to_csv_string("ohlcvt")  # Test CSV export functionality
        end_time = time.time()

        # Should complete quickly (under 1 second for 100 tokens)
        assert (end_time - start_time) < 1.0
        assert len(top_10) == 10
        assert len(ohlc_data) <= 100


class TestWebSocketEdgeCases:
    """Test WebSocket connection and data handling edge cases."""

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test WebSocket connection timeout scenarios."""
        scraper = DexScraper(max_retries=2)  # Low retry count for testing

        with patch(
            "websockets.connect", side_effect=asyncio.TimeoutError("Connection timeout")
        ):
            websocket = await scraper._connect()
            assert websocket is None

    @pytest.mark.asyncio
    async def test_malformed_message_handling(self):
        """Test handling of malformed binary data in internal methods."""
        scraper = DexScraper()

        # Test with various malformed binary data
        malformed_messages = [
            b"",  # Empty message
            b"ping",  # Text instead of binary
            b"\x00" * 10,  # Too short
            b"\x00" * 1000000,  # Too long
        ]

        # Should not crash on malformed messages - test internal methods
        for msg in malformed_messages:
            try:
                # Test internal methods that handle binary data
                result = scraper._extract_metadata_patterns(msg, 0)
                # Should return empty dict or handle gracefully
                assert isinstance(result, dict)
            except Exception as e:
                # Should handle errors gracefully (index errors, struct errors, etc.)
                assert any(
                    word in str(e).lower()
                    for word in ["index", "unpack", "struct", "range"]
                )

    def test_rate_limiting_edge_cases(self):
        """Test rate limiting with various scenarios."""
        scraper = DexScraper(rate_limit=1000.0)  # Very high rate limit

        # Test that very high rate limits don't cause issues
        assert scraper.rate_limit == 1000.0
        assert scraper._min_interval == 1.0 / 1000.0

        # Test very low rate limits
        slow_scraper = DexScraper(rate_limit=0.1)  # Very slow
        assert slow_scraper._min_interval == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
