"""Data models for DexScreener trading pairs and market data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class PriceData:
    """Price information for a trading pair."""
    current: float
    usd: float
    change_24h: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": str(self.current),
            "priceUsd": str(self.usd),
            "priceChange": {"h24": str(self.change_24h)} if self.change_24h is not None else None
        }


@dataclass
class LiquidityData:
    """Liquidity information for a trading pair."""
    usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {"liquidity": {"usd": str(self.usd)}}


@dataclass
class VolumeData:
    """Volume information for a trading pair."""
    h24: float

    def to_dict(self) -> Dict[str, Any]:
        return {"volume": {"h24": str(self.h24)}}


@dataclass
class OHLCData:
    """OHLC (Open, High, Low, Close) data for MetaTrader compatibility."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_mt5_format(self) -> str:
        """Format for MetaTrader 5 import."""
        dt = datetime.fromtimestamp(self.timestamp)
        return f"{dt.strftime('%Y.%m.%d %H:%M:%S')},{self.open:.8f},{self.high:.8f},{self.low:.8f},{self.close:.8f},{int(self.volume)}"


@dataclass
class TradingPair:
    """Complete trading pair information from DexScreener."""
    chain: str
    protocol: str
    pair_address: str
    base_token_name: str
    base_token_symbol: str
    base_token_address: str
    price_data: Optional[PriceData] = None
    liquidity_data: Optional[LiquidityData] = None
    volume_data: Optional[VolumeData] = None
    fdv: Optional[float] = None
    created_at: Optional[int] = None
    created_at_formatted: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching original output."""
        result = {
            "chain": self.chain,
            "protocol": self.protocol,
            "pairAddress": self.pair_address,
            "baseTokenName": self.base_token_name,
            "baseTokenSymbol": self.base_token_symbol,
            "baseTokenAddress": self.base_token_address,
        }

        if self.price_data:
            result.update(self.price_data.to_dict())
        
        if self.liquidity_data:
            result.update(self.liquidity_data.to_dict())
        
        if self.volume_data:
            result.update(self.volume_data.to_dict())
        
        if self.fdv is not None:
            result["fdv"] = str(self.fdv)
        
        if self.created_at is not None:
            result["pairCreatedAt"] = self.created_at
        
        if self.created_at_formatted:
            result["pairCreatedAtFormatted"] = self.created_at_formatted

        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def to_ohlc(self, timeframe: str = "1m") -> Optional[OHLCData]:
        """Convert current price data to OHLC format for MetaTrader."""
        if not self.price_data or not self.volume_data or not self.created_at:
            return None
        
        # For real OHLC data, we'd need historical data
        # This is a simplified version using current price as OHLC
        price = self.price_data.current
        return OHLCData(
            timestamp=self.created_at,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=self.volume_data.h24
        )