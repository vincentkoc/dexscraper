"""Configuration and filtering options for DexScreener scraper."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Chain(Enum):
    """Supported blockchain networks."""

    SOLANA = "solana"
    ETHEREUM = "ethereum"
    BASE = "base"
    BSC = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    AVALANCHE = "avalanche"


class Timeframe(Enum):
    """Supported timeframes."""

    M5 = "m5"  # 5 minutes
    H1 = "h1"  # 1 hour
    H6 = "h6"  # 6 hours
    H24 = "h24"  # 24 hours


class RankBy(Enum):
    """Supported ranking methods."""

    TRENDING_SCORE_H6 = "trendingScoreH6"
    VOLUME = "volume"
    TRANSACTIONS = "txns"
    PRICE_CHANGE_H24 = "priceChangeH24"
    PRICE_CHANGE_H6 = "priceChangeH6"
    PRICE_CHANGE_H1 = "priceChangeH1"
    LIQUIDITY = "liquidity"
    FDV = "fdv"
    MARKET_CAP = "marketCap"


class Order(Enum):
    """Sort order."""

    DESC = "desc"
    ASC = "asc"


class DEX(Enum):
    """Popular DEX identifiers."""

    # Solana DEXs
    RAYDIUM = "raydium"
    PUMPFUN = "pumpfun"
    PUMPSWAP = "pumpswap"
    ORCA = "orca"
    JUPITER = "jupiter"
    METEORA = "meteora"

    # Ethereum DEXs
    UNISWAP_V2 = "uniswap"
    UNISWAP_V3 = "uniswapv3"
    SUSHISWAP = "sushiswap"
    PANCAKESWAP = "pancakeswap"

    # Base DEXs
    AERODROME = "aerodrome"
    BASESWAP = "baseswap"


@dataclass
class Filters:
    """Complete filter configuration for DexScreener queries."""

    # Chain filters
    chain_ids: List[Chain] = field(default_factory=lambda: [Chain.SOLANA])

    # DEX filters
    dex_ids: List[DEX] = field(default_factory=list)

    # Liquidity filters
    liquidity_min: Optional[int] = None
    liquidity_max: Optional[int] = None

    # Volume filters
    volume_h24_min: Optional[int] = None
    volume_h24_max: Optional[int] = None
    volume_h6_min: Optional[int] = None
    volume_h6_max: Optional[int] = None
    volume_h1_min: Optional[int] = None
    volume_h1_max: Optional[int] = None

    # Transaction filters
    txns_h24_min: Optional[int] = None
    txns_h24_max: Optional[int] = None
    txns_h6_min: Optional[int] = None
    txns_h6_max: Optional[int] = None
    txns_h1_min: Optional[int] = None
    txns_h1_max: Optional[int] = None

    # Age filters
    pair_age_min: Optional[int] = None  # hours
    pair_age_max: Optional[int] = None  # hours

    # Price change filters
    price_change_h24_min: Optional[float] = None
    price_change_h24_max: Optional[float] = None
    price_change_h6_min: Optional[float] = None
    price_change_h6_max: Optional[float] = None
    price_change_h1_min: Optional[float] = None
    price_change_h1_max: Optional[float] = None

    # Market cap / FDV filters
    fdv_min: Optional[int] = None
    fdv_max: Optional[int] = None
    market_cap_min: Optional[int] = None
    market_cap_max: Optional[int] = None

    # Enhanced features
    enhanced_token_info: bool = False
    active_boosts_min: Optional[int] = None
    recent_purchased_impressions_min: Optional[int] = None

    # Pumpfun specific filters
    max_age: Optional[int] = None  # hours
    profile: Optional[int] = None  # Include profile data (0 or 1)
    max_launchpad_progress: Optional[float] = None  # Max launchpad progress %

    def to_query_params(self) -> Dict[str, str]:
        """Convert filters to WebSocket query parameters."""
        params = {}

        # Chain IDs
        for i, chain in enumerate(self.chain_ids):
            params[f"filters[chainIds][{i}]"] = chain.value

        # DEX IDs
        for i, dex in enumerate(self.dex_ids):
            params[f"filters[dexIds][{i}]"] = dex.value

        # Liquidity
        if self.liquidity_min is not None:
            params["filters[liquidity][min]"] = str(self.liquidity_min)
        if self.liquidity_max is not None:
            params["filters[liquidity][max]"] = str(self.liquidity_max)

        # Volume H24
        if self.volume_h24_min is not None:
            params["filters[volume][h24][min]"] = str(self.volume_h24_min)
        if self.volume_h24_max is not None:
            params["filters[volume][h24][max]"] = str(self.volume_h24_max)

        # Volume H6
        if self.volume_h6_min is not None:
            params["filters[volume][h6][min]"] = str(self.volume_h6_min)
        if self.volume_h6_max is not None:
            params["filters[volume][h6][max]"] = str(self.volume_h6_max)

        # Volume H1
        if self.volume_h1_min is not None:
            params["filters[volume][h1][min]"] = str(self.volume_h1_min)
        if self.volume_h1_max is not None:
            params["filters[volume][h1][max]"] = str(self.volume_h1_max)

        # Transactions H24
        if self.txns_h24_min is not None:
            params["filters[txns][h24][min]"] = str(self.txns_h24_min)
        if self.txns_h24_max is not None:
            params["filters[txns][h24][max]"] = str(self.txns_h24_max)

        # Transactions H6
        if self.txns_h6_min is not None:
            params["filters[txns][h6][min]"] = str(self.txns_h6_min)
        if self.txns_h6_max is not None:
            params["filters[txns][h6][max]"] = str(self.txns_h6_max)

        # Transactions H1
        if self.txns_h1_min is not None:
            params["filters[txns][h1][min]"] = str(self.txns_h1_min)
        if self.txns_h1_max is not None:
            params["filters[txns][h1][max]"] = str(self.txns_h1_max)

        # Pair age
        if self.pair_age_min is not None:
            params["filters[pairAge][min]"] = str(self.pair_age_min)
        if self.pair_age_max is not None:
            params["filters[pairAge][max]"] = str(self.pair_age_max)

        # Price change H24
        if self.price_change_h24_min is not None:
            params["filters[priceChange][h24][min]"] = str(self.price_change_h24_min)
        if self.price_change_h24_max is not None:
            params["filters[priceChange][h24][max]"] = str(self.price_change_h24_max)

        # Price change H6
        if self.price_change_h6_min is not None:
            params["filters[priceChange][h6][min]"] = str(self.price_change_h6_min)
        if self.price_change_h6_max is not None:
            params["filters[priceChange][h6][max]"] = str(self.price_change_h6_max)

        # Price change H1
        if self.price_change_h1_min is not None:
            params["filters[priceChange][h1][min]"] = str(self.price_change_h1_min)
        if self.price_change_h1_max is not None:
            params["filters[priceChange][h1][max]"] = str(self.price_change_h1_max)

        # FDV
        if self.fdv_min is not None:
            params["filters[fdv][min]"] = str(self.fdv_min)
        if self.fdv_max is not None:
            params["filters[fdv][max]"] = str(self.fdv_max)

        # Market cap
        if self.market_cap_min is not None:
            params["filters[marketCap][min]"] = str(self.market_cap_min)
        if self.market_cap_max is not None:
            params["filters[marketCap][max]"] = str(self.market_cap_max)

        # Enhanced features
        if self.enhanced_token_info:
            params["filters[enhancedTokenInfo]"] = "true"
        if self.active_boosts_min is not None:
            params["filters[activeBoosts][min]"] = str(self.active_boosts_min)
        if self.recent_purchased_impressions_min is not None:
            params["filters[recentPurchasedImpressions][min]"] = str(
                self.recent_purchased_impressions_min
            )

        # Pumpfun specific parameters
        if self.max_age is not None:
            params["maxAge"] = str(self.max_age)
        if self.profile is not None:
            params["profile"] = str(self.profile)
        if self.max_launchpad_progress is not None:
            params["maxLaunchpadProgress"] = str(self.max_launchpad_progress)

        return params


@dataclass
class ScrapingConfig:
    """Complete configuration for DexScreener scraping."""

    timeframe: Timeframe = Timeframe.H24
    rank_by: RankBy = RankBy.TRENDING_SCORE_H6
    order: Order = Order.DESC
    filters: Filters = field(default_factory=Filters)

    def build_websocket_url(self) -> str:
        """Build the complete WebSocket URL with all parameters."""
        base_url = (
            f"wss://io.dexscreener.com/dex/screener/v5/pairs/{self.timeframe.value}/1"
        )

        params = {
            "rankBy[key]": self.rank_by.value,
            "rankBy[order]": self.order.value,
        }

        # Add filter parameters
        params.update(self.filters.to_query_params())

        # Build query string
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={value}")

        return f"{base_url}?{'&'.join(query_parts)}"


# Predefined configurations for common use cases
class PresetConfigs:
    """Predefined configurations for common scraping scenarios."""

    @staticmethod
    def trending(
        chain: Chain = Chain.SOLANA, timeframe: Timeframe = Timeframe.H24
    ) -> ScrapingConfig:
        """Trending pairs configuration."""
        return ScrapingConfig(
            timeframe=timeframe,
            rank_by=RankBy.TRENDING_SCORE_H6,
            order=Order.DESC,
            filters=Filters(chain_ids=[chain]),
        )

    @staticmethod
    def top_volume(
        chain: Chain = Chain.SOLANA, min_liquidity: int = 25000, min_txns: int = 50
    ) -> ScrapingConfig:
        """Top volume pairs configuration."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.VOLUME,
            order=Order.DESC,
            filters=Filters(
                chain_ids=[chain], liquidity_min=min_liquidity, txns_h24_min=min_txns
            ),
        )

    @staticmethod
    def gainers(
        chain: Chain = Chain.SOLANA, min_liquidity: int = 25000, min_volume: int = 10000
    ) -> ScrapingConfig:
        """Price gainers configuration."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.PRICE_CHANGE_H24,
            order=Order.DESC,
            filters=Filters(
                chain_ids=[chain],
                liquidity_min=min_liquidity,
                volume_h24_min=min_volume,
                txns_h24_min=50,
            ),
        )

    @staticmethod
    def new_pairs(
        chain: Chain = Chain.SOLANA, max_age_hours: int = 24
    ) -> ScrapingConfig:
        """New pairs configuration."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.TRENDING_SCORE_H6,
            order=Order.DESC,
            filters=Filters(chain_ids=[chain], pair_age_max=max_age_hours),
        )

    @staticmethod
    def top_transactions(chain: Chain = Chain.SOLANA) -> ScrapingConfig:
        """Top transaction count configuration."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.TRANSACTIONS,
            order=Order.DESC,
            filters=Filters(chain_ids=[chain]),
        )

    @staticmethod
    def boosted_only(chain: Chain = Chain.SOLANA) -> ScrapingConfig:
        """Only boosted pairs configuration."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.TRENDING_SCORE_H6,
            order=Order.DESC,
            filters=Filters(
                chain_ids=[chain], enhanced_token_info=True, active_boosts_min=1
            ),
        )

    @staticmethod
    def pumpfun_trending(
        dex: DEX = DEX.PUMPFUN, max_age: int = 3, max_launchpad_progress: float = 99.99
    ) -> ScrapingConfig:
        """Pumpfun trending configuration matching validated URL parameters."""
        return ScrapingConfig(
            timeframe=Timeframe.H1,
            rank_by=RankBy.TRENDING_SCORE_H6,
            order=Order.DESC,
            filters=Filters(
                chain_ids=[Chain.SOLANA],
                dex_ids=[dex],
                max_age=max_age,
                profile=1,
                max_launchpad_progress=max_launchpad_progress,
            ),
        )
