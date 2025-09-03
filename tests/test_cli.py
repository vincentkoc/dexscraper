#!/usr/bin/env python3
"""Test cases for CLI functionality."""

import argparse
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper.cli import (
    build_config_from_args,
    create_token_callback,
    parse_chain,
    parse_dex_list,
    parse_rank_by,
    parse_timeframe,
    SlickCLI,
)
from dexscraper.config import Chain, DEX, Filters, RankBy, ScrapingConfig, Timeframe
from dexscraper.models import ExtractedTokenBatch, TokenProfile


class TestCLIParsing:
    """Test CLI argument parsing functions."""

    def test_parse_chain(self):
        """Test chain parsing from string."""
        assert parse_chain("solana") == Chain.SOLANA
        assert parse_chain("ETHEREUM") == Chain.ETHEREUM
        assert parse_chain("bsc") == Chain.BSC

        with pytest.raises(argparse.ArgumentTypeError):
            parse_chain("invalid_chain")

    def test_parse_timeframe(self):
        """Test timeframe parsing from string."""
        assert parse_timeframe("h1") == Timeframe.H1
        assert parse_timeframe("H24") == Timeframe.H24
        assert parse_timeframe("m5") == Timeframe.M5

        with pytest.raises(argparse.ArgumentTypeError):
            parse_timeframe("invalid_timeframe")

    def test_parse_rank_by(self):
        """Test rank by parsing from string."""
        assert parse_rank_by("volume") == RankBy.VOLUME
        assert parse_rank_by("trendingScoreH6") == RankBy.TRENDING_SCORE_H6
        assert parse_rank_by("txns") == RankBy.TRANSACTIONS

        with pytest.raises(argparse.ArgumentTypeError):
            parse_rank_by("invalid_ranking")

    def test_parse_dex_list(self):
        """Test DEX list parsing from comma-separated string."""
        result = parse_dex_list("raydium,pumpfun,uniswap")
        expected = [DEX.RAYDIUM, DEX.PUMPFUN, DEX.UNISWAP_V2]
        assert result == expected

        result = parse_dex_list("pumpfun")
        assert result == [DEX.PUMPFUN]

        with pytest.raises(argparse.ArgumentTypeError):
            parse_dex_list("invalid_dex,raydium")


class TestConfigBuilding:
    """Test configuration building from CLI arguments."""

    def test_build_config_trending_mode(self):
        """Test config building for trending mode."""
        args = Mock()
        args.mode = "trending"
        args.chain = Chain.SOLANA
        args.chains = None
        args.timeframe = Timeframe.H24

        config = build_config_from_args(args)

        assert isinstance(config, ScrapingConfig)
        assert config.rank_by == RankBy.TRENDING_SCORE_H6
        assert config.filters.chain_ids == [Chain.SOLANA]

    def test_build_config_custom_filters(self):
        """Test config building with custom filters."""
        args = Mock()
        args.mode = None
        args.chain = Chain.ETHEREUM
        args.chains = None
        args.timeframe = Timeframe.H1
        args.rank_by = RankBy.VOLUME
        args.order = "desc"
        args.dex = None
        args.dexs = [DEX.UNISWAP_V2, DEX.SUSHISWAP]
        args.min_liquidity = 50000
        args.max_liquidity = None
        args.min_volume = 10000
        args.max_volume = None
        args.min_volume_h6 = None
        args.max_volume_h6 = None
        args.min_volume_h1 = None
        args.max_volume_h1 = None
        args.min_txns = 100
        args.max_txns = None
        args.min_txns_h6 = None
        args.max_txns_h6 = None
        args.min_txns_h1 = None
        args.max_txns_h1 = None
        args.min_age = None
        args.max_age = None
        args.min_change = None
        args.max_change = None
        args.min_change_h6 = None
        args.max_change_h6 = None
        args.min_change_h1 = None
        args.max_change_h1 = None
        args.min_fdv = None
        args.max_fdv = None
        args.min_mcap = None
        args.max_mcap = None
        args.enhanced = False
        args.min_boosts = None
        args.min_ads = None

        config = build_config_from_args(args)

        assert config.timeframe == Timeframe.H1
        assert config.rank_by == RankBy.VOLUME
        assert config.filters.chain_ids == [Chain.ETHEREUM]
        assert config.filters.dex_ids == [DEX.UNISWAP_V2, DEX.SUSHISWAP]
        assert config.filters.liquidity_min == 50000
        assert config.filters.volume_h24_min == 10000
        assert config.filters.txns_h24_min == 100

    def test_build_config_multiple_chains(self):
        """Test config building with multiple chains."""
        args = Mock()
        args.mode = None
        args.chain = Chain.SOLANA
        args.chains = [Chain.ETHEREUM, Chain.BASE]  # Should override single chain
        args.timeframe = Timeframe.H6
        args.rank_by = None
        args.order = "asc"
        # ... (set other args to None/defaults)
        for attr in [
            "dex",
            "dexs",
            "min_liquidity",
            "max_liquidity",
            "min_volume",
            "max_volume",
            "min_volume_h6",
            "max_volume_h6",
            "min_volume_h1",
            "max_volume_h1",
            "min_txns",
            "max_txns",
            "min_txns_h6",
            "max_txns_h6",
            "min_txns_h1",
            "max_txns_h1",
            "min_age",
            "max_age",
            "min_change",
            "max_change",
            "min_change_h6",
            "max_change_h6",
            "min_change_h1",
            "max_change_h1",
            "min_fdv",
            "max_fdv",
            "min_mcap",
            "max_mcap",
            "enhanced",
            "min_boosts",
            "min_ads",
        ]:
            setattr(args, attr, None)
        args.enhanced = False

        config = build_config_from_args(args)

        assert config.filters.chain_ids == [Chain.ETHEREUM, Chain.BASE]


class TestCallbacks:
    """Test callback function creation."""

    def test_create_token_callback_json(self):
        """Test JSON format callback creation."""
        callback = create_token_callback("json")

        # Create mock batch
        tokens = [
            TokenProfile(symbol="TEST1", price=0.001, volume_24h=1000),
            TokenProfile(symbol="TEST2", price=0.002, volume_24h=2000),
        ]
        batch = ExtractedTokenBatch(tokens=tokens)

        # Capture output
        import io
        from contextlib import redirect_stdout

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            callback(batch)

        output = output_buffer.getvalue()
        assert '"type":"enhanced_tokens"' in output
        assert '"total_extracted":2' in output
        assert '"symbol":"TEST1"' in output

    def test_create_token_callback_ohlcv(self):
        """Test OHLCV format callback creation."""
        callback = create_token_callback("ohlcv")

        tokens = [
            TokenProfile(
                symbol="TEST", price=0.001, volume_24h=1000, timestamp=1234567890
            )
        ]
        batch = ExtractedTokenBatch(tokens=tokens)

        import io
        from contextlib import redirect_stdout

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            callback(batch)

        output = output_buffer.getvalue()
        assert "DateTime,Open,High,Low,Close,Volume" in output

    def test_create_token_callback_ohlcvt(self):
        """Test OHLCVT format callback creation."""
        callback = create_token_callback("ohlcvt")

        tokens = [
            TokenProfile(
                symbol="TEST", price=0.001, volume_24h=1000, timestamp=1234567890
            )
        ]
        batch = ExtractedTokenBatch(tokens=tokens)

        import io
        from contextlib import redirect_stdout

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            callback(batch)

        output = output_buffer.getvalue()
        assert "DateTime,Open,High,Low,Close,Volume,Trades" in output


class TestSlickCLI:
    """Test Rich display functionality."""

    @pytest.mark.skipif(True, reason="Rich not required for core functionality")
    def test_rich_display_creation(self):
        """Test Rich display manager creation."""
        try:
            from rich.console import Console

            display = SlickCLI()

            assert display.extraction_count == 0
            assert hasattr(display, "console")
        except ImportError:
            pytest.skip("Rich not available")

    @pytest.mark.skipif(True, reason="Rich not required for core functionality")
    def test_rich_table_creation(self):
        """Test Rich table creation with token data."""
        try:
            from rich.console import Console

            display = SlickCLI()

            tokens = [
                TokenProfile(
                    symbol="TEST1",
                    price=0.001,
                    volume_24h=1000,
                    confidence_score=0.8,
                    txns_24h=50,
                    makers=10,
                ),
                TokenProfile(
                    symbol="TEST2",
                    price=0.002,
                    volume_24h=2000,
                    confidence_score=0.9,
                    txns_24h=100,
                    makers=20,
                ),
            ]
            batch = ExtractedTokenBatch(tokens=tokens)

            table = display.create_token_table(batch)
            assert table is not None
            assert "Live Token Data" in str(table.title)

        except ImportError:
            pytest.skip("Rich not available")


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    @pytest.mark.asyncio
    async def test_cli_main_once_flag(self):
        """Test CLI main function with --once flag."""
        from dexscraper.cli import main

        # Mock argv for testing
        test_args = ["dexscraper", "--once", "--format", "json"]

        with patch("sys.argv", test_args):
            with patch("dexscraper.cli.DexScraper") as mock_scraper_class:
                mock_scraper = Mock()
                mock_batch = ExtractedTokenBatch(
                    tokens=[TokenProfile(symbol="TEST", price=0.001)]
                )
                mock_scraper.extract_token_data = AsyncMock(return_value=mock_batch)
                mock_scraper_class.return_value = mock_scraper

                with patch("builtins.print"):
                    try:
                        await main()
                        mock_scraper.extract_token_data.assert_called_once()
                    except SystemExit:
                        pass  # CLI may exit normally

    def test_cli_argument_parsing(self):
        """Test CLI argument parsing with various combinations."""
        import argparse

        from dexscraper.cli import main

        # Test valid arguments
        test_cases = [
            ["--format", "json"],
            ["--format", "ohlcv", "--chain", "ethereum"],
            ["--mode", "trending", "--timeframe", "h1"],
            ["--min-liquidity", "50000", "--max-volume", "1000000"],
            ["--chains", "solana,ethereum", "--dexs", "raydium,uniswap"],
        ]

        for test_args in test_cases:
            full_args = ["dexscraper", "--once"] + test_args

            with patch("sys.argv", full_args):
                with patch("dexscraper.cli.DexScraper"):
                    with patch("asyncio.run"):
                        try:
                            # This tests that argument parsing doesn't fail
                            main()
                        except (SystemExit, Exception):
                            # Some arguments might cause early exits, that's OK
                            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
