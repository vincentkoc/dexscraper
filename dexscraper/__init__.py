"""DexScreener WebSocket scraper package for real-time cryptocurrency data."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

from .config import (
    DEX,
    Chain,
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

            version = get_version(root="..", relative_to=__file__)
            return str(version)
        except (ImportError, PackageNotFoundError, OSError):
            return "0.0.0"


__version__ = _resolve_version()
__author__ = "Vincent Koc"

__all__ = [
    "DEX",
    "Chain",
    "DexScraper",
    "ExtractedTokenBatch",
    "Filters",
    "LiquidityData",
    "OHLCData",
    "Order",
    "PresetConfigs",
    "PriceData",
    "RankBy",
    "ScrapingConfig",
    "Timeframe",
    "TokenProfile",
    "TradingPair",
    "VolumeData",
]
