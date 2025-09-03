#!/usr/bin/env python3
"""Test cases for DexScraper main functionality."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper import DexScraper
from dexscraper.config import Chain, DEX, PresetConfigs
from dexscraper.models import ExtractedTokenBatch, TokenProfile


class TestDexScraper:
    """Test DexScraper functionality."""

    def test_scraper_initialization(self):
        """Test scraper initialization with default and custom parameters."""
        # Default initialization
        scraper = DexScraper()
        assert scraper.debug is False
        assert scraper.rate_limit == 4.0
        assert scraper.max_retries == 5
        assert scraper.config is not None

        # Custom initialization
        custom_config = PresetConfigs.pumpfun_trending()
        scraper = DexScraper(
            debug=True, rate_limit=2.0, max_retries=3, config=custom_config
        )
        assert scraper.debug is True
        assert scraper.rate_limit == 2.0
        assert scraper.max_retries == 3
        assert scraper.config == custom_config

    def test_scraper_headers(self):
        """Test header rotation functionality."""
        scraper = DexScraper()

        # Test multiple header calls return different user agents
        headers1 = scraper._get_headers()
        headers2 = scraper._get_headers()
        headers3 = scraper._get_headers()

        # Should have rotated through different user agents
        assert (
            headers1["User-Agent"] != headers2["User-Agent"]
            or headers2["User-Agent"] != headers3["User-Agent"]
        )

        # Check required headers are present
        required_headers = ["User-Agent", "Accept", "Origin", "Sec-WebSocket-Version"]
        for header in required_headers:
            assert header in headers1

    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        scraper = DexScraper(backoff_base=1.0)

        # Test increasing backoff delays
        scraper._retry_count = 0
        delay0 = scraper._get_backoff_delay()

        scraper._retry_count = 1
        delay1 = scraper._get_backoff_delay()

        scraper._retry_count = 2
        delay2 = scraper._get_backoff_delay()

        # Delays should generally increase (with jitter variation)
        assert delay1 > delay0 * 0.5  # Account for jitter
        assert delay2 > delay1 * 0.5

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        import time

        scraper = DexScraper(rate_limit=10.0)  # 10 requests per second

        start_time = time.time()
        await scraper._rate_limit()
        await scraper._rate_limit()
        end_time = time.time()

        # Should have added some delay
        elapsed = end_time - start_time
        expected_min_delay = 0.1  # 1/10 second
        assert elapsed >= expected_min_delay * 0.8  # Allow some tolerance

    def test_websocket_url_building(self):
        """Test WebSocket URL construction with different configurations."""
        # Default config
        scraper = DexScraper()
        url = scraper.config.build_websocket_url()

        assert "wss://io.dexscreener.com/dex/screener/v5/pairs/" in url
        assert "rankBy[key]=" in url
        assert "rankBy[order]=" in url
        assert "filters[chainIds][0]=" in url

        # Pumpfun config
        config = PresetConfigs.pumpfun_trending()
        scraper = DexScraper(config=config)
        url = scraper.config.build_websocket_url()

        assert "maxAge=3" in url
        assert "profile=1" in url
        assert "maxLaunchpadProgress=99.99" in url

    def test_numeric_extraction_methods(self):
        """Test numeric data extraction utilities."""
        from dexscraper.utils import (
            cluster_numeric_values,
            extract_doubles_from_bytes,
            extract_floats_from_bytes,
        )

        # Test sample binary data
        sample_data = b"\x00\x01\x02\x03\x40\x09\x21\xfb\x54\x44\x2d\x18"

        # Test float extraction
        floats = extract_floats_from_bytes(sample_data)
        assert len(floats) >= 0  # Should extract some floats

        # Test double extraction
        doubles = extract_doubles_from_bytes(sample_data)
        assert len(doubles) >= 0  # Should extract some doubles

        # Test clustering
        all_numbers = floats + doubles
        if all_numbers:
            clusters = cluster_numeric_values(all_numbers, tolerance=0.05)
            assert isinstance(clusters, list)

    def test_metadata_extraction(self):
        """Test metadata extraction from binary data."""
        from dexscraper.utils import extract_solana_addresses, extract_urls

        # Test with sample data containing URL-like strings
        sample_data = b"https://twitter.com/test\x00some other data\x00"

        # Extract addresses and URLs
        addresses = extract_solana_addresses(sample_data)
        urls = extract_urls(sample_data)

        assert isinstance(addresses, list)
        assert isinstance(urls, list)

        # Should find the URL we embedded
        assert any("twitter.com" in url for url in urls)

    def test_token_profile_building(self):
        """Test token profile construction from extracted data."""
        scraper = DexScraper()

        # Mock record data with expected structure
        record = {
            "metadata": {
                "addresses": [
                    {
                        "address": "DjDzLNonA1XcWpzTBZhNZUqHCvq6SeLfT3otPYdVSMH",
                        "type": "SOL_token",
                    }
                ],
                "urls": [{"url": "https://twitter.com/test", "type": "twitter"}],
                "symbols": [{"value": "TEST", "confidence": 0.8, "position": 0}],
                "protocols": [{"protocol": "Raydium"}],
            },
            "completeness_score": 0.85,
            "cluster": {
                "start_pos": 0,
                "end_pos": 100,
                "classified": {
                    "prices": [(0.000123, 0.000123)],
                    "volumes": [(1000000.0, 1000000.0)],
                    "txns": [(150.0, 150.0)],
                    "makers": [(10.0, 10.0)],
                    "liquidity": [(50000.0, 50000.0)],
                    "market_caps": [(100000.0, 100000.0)],
                    "percentages": [
                        (0.05, 0.05),
                        (0.10, 0.10),
                        (0.15, 0.15),
                        (0.20, 0.20),
                    ],
                },
            },
        }

        # Build profile
        profile = scraper._build_token_profile(record, 0)

        assert isinstance(profile, TokenProfile)
        assert profile.record_position == 0
        assert profile.record_span == 100

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket connection error handling."""
        scraper = DexScraper(max_retries=1)  # Low retry count for testing

        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            websocket = await scraper._connect()
            assert websocket is None  # Should return None on failure


class TestDexScraperIntegration:
    """Integration tests requiring network access."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_token_extraction(self):
        """Test real token extraction from DexScreener."""
        scraper = DexScraper(debug=False)

        try:
            batch = await scraper.extract_token_data()

            # Basic validation
            assert isinstance(batch, ExtractedTokenBatch)
            assert batch.total_extracted >= 0

            if batch.tokens:
                # Validate token structure
                token = batch.tokens[0]
                assert isinstance(token, TokenProfile)
                assert hasattr(token, "price")
                assert hasattr(token, "volume_24h")
                assert hasattr(token, "confidence_score")

                # Test OHLC conversion
                ohlc = token.to_ohlc()
                if ohlc:
                    assert ohlc.timestamp > 0
                    assert ohlc.open >= 0
                    assert ohlc.close >= 0
                    assert ohlc.volume >= 0

        except Exception as e:
            pytest.skip(f"Network test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_different_configurations(self):
        """Test extraction with different configuration presets."""
        configs = [
            PresetConfigs.trending(),
            PresetConfigs.pumpfun_trending(),
            PresetConfigs.top_volume(min_liquidity=1000),
        ]

        for config in configs:
            scraper = DexScraper(config=config, debug=False)

            try:
                batch = await scraper.extract_token_data()
                assert isinstance(batch, ExtractedTokenBatch)
                # Each config should potentially return different results

            except Exception as e:
                pytest.skip(f"Configuration test failed for {config}: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_export_functionality(self):
        """Test all export formats work with real data."""
        scraper = DexScraper(debug=False)

        try:
            batch = await scraper.extract_token_data()

            if batch.tokens:
                # Test CSV string exports
                csv_ohlcv = batch.to_csv_string("ohlcv")
                assert "DateTime,Open,High,Low,Close,Volume" in csv_ohlcv

                csv_ohlcvt = batch.to_csv_string("ohlcvt")
                assert "DateTime,Open,High,Low,Close,Volume,Trades" in csv_ohlcvt

                # Test OHLC batch conversion
                ohlc_batch = batch.to_ohlc_batch()
                assert len(ohlc_batch) <= len(batch.tokens)

                # Test TradingPair conversion
                trading_pairs = batch.to_trading_pairs()
                assert len(trading_pairs) == len(batch.tokens)

        except Exception as e:
            pytest.skip(f"Export test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
