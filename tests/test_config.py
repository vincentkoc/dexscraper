#!/usr/bin/env python3
"""Test cases for dexscraper configuration and URL building."""

import pytest

from dexscraper.config import (
    Chain,
    DEX,
    Filters,
    Order,
    PresetConfigs,
    RankBy,
    ScrapingConfig,
    Timeframe,
)


class TestFilters:
    """Test Filters configuration."""

    def test_default_filters(self):
        """Test default filter values."""
        filters = Filters()
        assert filters.chain_ids == [Chain.SOLANA]
        assert filters.dex_ids == []
        assert filters.liquidity_min is None
        assert not filters.enhanced_token_info

    def test_pumpfun_filters(self):
        """Test Pumpfun-specific filters."""
        filters = Filters(max_age=3, profile=1, max_launchpad_progress=99.99)
        params = filters.to_query_params()

        assert params["maxAge"] == "3"
        assert params["profile"] == "1"
        assert params["maxLaunchpadProgress"] == "99.99"

    def test_complex_filters(self):
        """Test complex filter combinations."""
        filters = Filters(
            chain_ids=[Chain.SOLANA, Chain.ETHEREUM],
            dex_ids=[DEX.PUMPFUN, DEX.RAYDIUM],
            liquidity_min=25000,
            liquidity_max=1000000,
            volume_h24_min=10000,
            txns_h24_min=50,
            enhanced_token_info=True,
            active_boosts_min=1,
        )

        params = filters.to_query_params()

        # Check chain IDs
        assert params["filters[chainIds][0]"] == "solana"
        assert params["filters[chainIds][1]"] == "ethereum"

        # Check DEX IDs
        assert params["filters[dexIds][0]"] == "pumpfun"
        assert params["filters[dexIds][1]"] == "raydium"

        # Check numeric filters
        assert params["filters[liquidity][min]"] == "25000"
        assert params["filters[liquidity][max]"] == "1000000"
        assert params["filters[volume][h24][min]"] == "10000"
        assert params["filters[txns][h24][min]"] == "50"

        # Check enhanced features
        assert params["filters[enhancedTokenInfo]"] == "true"
        assert params["filters[activeBoosts][min]"] == "1"


class TestScrapingConfig:
    """Test ScrapingConfig and URL building."""

    def test_default_config(self):
        """Test default configuration."""
        config = ScrapingConfig()
        assert config.timeframe == Timeframe.H24
        assert config.rank_by == RankBy.TRENDING_SCORE_H6
        assert config.order == Order.DESC

    def test_websocket_url_building(self):
        """Test WebSocket URL construction."""
        config = ScrapingConfig(
            timeframe=Timeframe.H1, rank_by=RankBy.VOLUME, order=Order.DESC
        )

        url = config.build_websocket_url()

        assert "wss://io.dexscreener.com/dex/screener/v5/pairs/h1/1" in url
        assert "rankBy[key]=volume" in url
        assert "rankBy[order]=desc" in url
        assert "filters[chainIds][0]=solana" in url

    def test_complex_url_building(self):
        """Test complex URL with many filters."""
        filters = Filters(
            chain_ids=[Chain.SOLANA],
            dex_ids=[DEX.PUMPFUN],
            liquidity_min=25000,
            max_age=3,
            profile=1,
            max_launchpad_progress=99.99,
        )

        config = ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.TRENDING_SCORE_H6,
            order=Order.DESC,
            filters=filters,
        )

        url = config.build_websocket_url()

        # Check base URL and core params
        assert "wss://io.dexscreener.com/dex/screener/v5/pairs/h1/1" in url
        assert "rankBy[key]=trendingScoreH6" in url
        assert "rankBy[order]=desc" in url

        # Check filter params
        assert "filters[chainIds][0]=solana" in url
        assert "filters[dexIds][0]=pumpfun" in url
        assert "filters[liquidity][min]=25000" in url

        # Check Pumpfun specific params
        assert "maxAge=3" in url
        assert "profile=1" in url
        assert "maxLaunchpadProgress=99.99" in url


class TestPresetConfigs:
    """Test preset configuration builders."""

    def test_trending_config(self):
        """Test trending preset."""
        config = PresetConfigs.trending()

        assert config.timeframe == Timeframe.H24
        assert config.rank_by == RankBy.TRENDING_SCORE_H6
        assert config.order == Order.DESC
        assert config.filters.chain_ids == [Chain.SOLANA]

    def test_trending_config_custom_chain(self):
        """Test trending preset with custom chain."""
        config = PresetConfigs.trending(Chain.ETHEREUM, Timeframe.H1)

        assert config.timeframe == Timeframe.H1
        assert config.filters.chain_ids == [Chain.ETHEREUM]

    def test_top_volume_config(self):
        """Test top volume preset."""
        config = PresetConfigs.top_volume(min_liquidity=50000, min_txns=100)

        assert config.timeframe == Timeframe.H1
        assert config.rank_by == RankBy.VOLUME
        assert config.filters.liquidity_min == 50000
        assert config.filters.txns_h24_min == 100

    def test_gainers_config(self):
        """Test gainers preset."""
        config = PresetConfigs.gainers(min_volume=20000)

        assert config.rank_by == RankBy.PRICE_CHANGE_H24
        assert config.filters.volume_h24_min == 20000
        assert config.filters.txns_h24_min == 50  # Default

    def test_new_pairs_config(self):
        """Test new pairs preset."""
        config = PresetConfigs.new_pairs(max_age_hours=12)

        assert config.rank_by == RankBy.TRENDING_SCORE_H6
        assert config.filters.pair_age_max == 12

    def test_boosted_only_config(self):
        """Test boosted only preset."""
        config = PresetConfigs.boosted_only()

        assert config.filters.enhanced_token_info is True
        assert config.filters.active_boosts_min == 1

    def test_pumpfun_trending_config(self):
        """Test Pumpfun trending preset."""
        config = PresetConfigs.pumpfun_trending()

        assert config.timeframe == Timeframe.H1
        assert config.rank_by == RankBy.TRENDING_SCORE_H6
        assert config.filters.dex_ids == [DEX.PUMPFUN]
        assert config.filters.max_age == 3
        assert config.filters.profile == 1
        assert config.filters.max_launchpad_progress == 99.99

        # Test URL matches the original validated pattern
        url = config.build_websocket_url()
        assert "maxAge=3" in url
        assert "profile=1" in url
        assert "maxLaunchpadProgress=99.99" in url
        assert "filters[dexIds][0]=pumpfun" in url

    def test_pumpfun_trending_custom_params(self):
        """Test Pumpfun trending with custom parameters."""
        config = PresetConfigs.pumpfun_trending(
            dex=DEX.RAYDIUM, max_age=6, max_launchpad_progress=95.0
        )

        assert config.filters.dex_ids == [DEX.RAYDIUM]
        assert config.filters.max_age == 6
        assert config.filters.max_launchpad_progress == 95.0


class TestEnumValues:
    """Test enum value correctness."""

    def test_chain_values(self):
        """Test chain enum values."""
        assert Chain.SOLANA.value == "solana"
        assert Chain.ETHEREUM.value == "ethereum"
        assert Chain.BASE.value == "base"

    def test_dex_values(self):
        """Test DEX enum values."""
        assert DEX.PUMPFUN.value == "pumpfun"
        assert DEX.RAYDIUM.value == "raydium"
        assert DEX.UNISWAP_V2.value == "uniswap"
        assert DEX.UNISWAP_V3.value == "uniswapv3"

    def test_timeframe_values(self):
        """Test timeframe enum values."""
        assert Timeframe.M5.value == "m5"
        assert Timeframe.H1.value == "h1"
        assert Timeframe.H6.value == "h6"
        assert Timeframe.H24.value == "h24"

    def test_rankby_values(self):
        """Test rank by enum values."""
        assert RankBy.TRENDING_SCORE_H6.value == "trendingScoreH6"
        assert RankBy.VOLUME.value == "volume"
        assert RankBy.TRANSACTIONS.value == "txns"
        assert RankBy.PRICE_CHANGE_H24.value == "priceChangeH24"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
