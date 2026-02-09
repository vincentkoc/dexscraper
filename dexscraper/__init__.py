"""DexScreener WebSocket scraper package for real-time cryptocurrency data."""

from importlib.metadata import PackageNotFoundError, version as package_version
from .config import (
    Chain,
    DEX,
    Filters,
    Order,
    PresetConfigs,
    RankBy,
    ScrapingConfig,
    Timeframe,
)
from .models import (
    ExtractedTokenBatch,
    LiquidityData,
    OHLCData,
    PriceData,
    TokenProfile,
    TradingPair,
    VolumeData,
)
from .scraper import DexScraper


def _resolve_version() -> str:
    """Resolve package version from installed metadata, with SCM fallback."""
    try:
        return package_version("dexscraper")
    except PackageNotFoundError:
        try:
            from setuptools_scm import get_version

            return get_version(root="..", relative_to=__file__)
        except Exception:
            return "0.0.0"


__version__ = _resolve_version()
__author__ = "Vincent Koc"

__all__ = [
    "DexScraper",
    "TradingPair",
    "PriceData",
    "LiquidityData",
    "VolumeData",
    "OHLCData",
    "TokenProfile",
    "ExtractedTokenBatch",
    "ScrapingConfig",
    "PresetConfigs",
    "Chain",
    "Timeframe",
    "RankBy",
    "Order",
    "DEX",
    "Filters",
]
