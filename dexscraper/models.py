"""Data models for DexScreener trading pairs and market data."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional


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
            "priceChange": (
                {"h24": str(self.change_24h)} if self.change_24h is not None else None
            ),
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
    trades: Optional[int] = None  # Number of trades (T in OHLCVT)

    def to_mt5_format(self) -> str:
        """Format for MetaTrader 5 import."""
        dt = datetime.fromtimestamp(self.timestamp)
        return f"{dt.strftime('%Y.%m.%d %H:%M:%S')},{self.open:.8f},{self.high:.8f},{self.low:.8f},{self.close:.8f},{int(self.volume)}"

    def to_csv_format(self) -> str:
        """Format for CSV export (OHLCV)."""
        dt = datetime.fromtimestamp(self.timestamp)
        return f"{dt.strftime('%Y-%m-%d %H:%M:%S')},{self.open:.8f},{self.high:.8f},{self.low:.8f},{self.close:.8f},{self.volume:.2f}"

    def to_ohlcvt_format(self) -> str:
        """Format for OHLCVT (Open, High, Low, Close, Volume, Trades) export."""
        dt = datetime.fromtimestamp(self.timestamp)
        trades_count = (
            self.trades if self.trades is not None else int(self.volume / 1000)
        )  # Estimate trades
        return f"{dt.strftime('%Y-%m-%d %H:%M:%S')},{self.open:.8f},{self.high:.8f},{self.low:.8f},{self.close:.8f},{self.volume:.2f},{trades_count}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trades": self.trades,
        }


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
        # Use real data from binary protocol extraction
        if self.price_data and self.volume_data and self.created_at:
            price = self.price_data.current
            volume = self.volume_data.h24
            timestamp = self.created_at
        else:
            # Create placeholder data when actual price/volume data isn't available
            timestamp = int(time.time())
            price = 1.0  # Placeholder price
            volume = 1000.0  # Placeholder volume

        return OHLCData(
            timestamp=timestamp,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume,
        )


@dataclass
class TokenProfile:
    """Complete token profile extracted from binary protocol with all metadata."""

    # Core Trading Data (from binary extraction)
    price: Optional[float] = None
    volume_24h: Optional[float] = None
    txns_24h: Optional[int] = None
    makers: Optional[int] = None
    liquidity: Optional[float] = None
    market_cap: Optional[float] = None

    # Token Identification
    symbol: Optional[str] = None
    token_name: Optional[str] = None
    chain: Optional[str] = None
    protocol: Optional[str] = None
    age: Optional[str] = None
    boost: Optional[int] = None

    # Addresses (Base58 Solana format)
    pair_address: Optional[str] = None
    creator_address: Optional[str] = None
    token_address: Optional[str] = None
    quote_address: Optional[str] = None

    # Social/Web Metadata
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None

    # Percentage Changes
    change_5m: Optional[float] = None
    change_1h: Optional[float] = None
    change_6h: Optional[float] = None
    change_24h: Optional[float] = None

    # Quality & Technical Metrics
    confidence_score: float = 0.0
    field_count: int = 0
    record_position: Optional[int] = None
    record_span: Optional[int] = None
    timestamp: Optional[int] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = int(time.time())

    def to_trading_pair(self) -> "TradingPair":
        """Convert TokenProfile to legacy TradingPair format for compatibility."""
        # Create price data
        price_data = None
        if self.price is not None:
            price_data = PriceData(
                current=self.price,
                usd=self.price,  # Assuming USD price
                change_24h=self.change_24h,
            )

        # Create volume data
        volume_data = None
        if self.volume_24h is not None:
            volume_data = VolumeData(h24=self.volume_24h)

        # Create liquidity data
        liquidity_data = None
        if self.liquidity is not None:
            liquidity_data = LiquidityData(usd=self.liquidity)

        # Create trading pair
        return TradingPair(
            chain=self.chain or "solana",
            protocol=self.protocol or "unknown",
            pair_address=self.pair_address or "unknown",
            base_token_name=self.token_name or self.symbol or "Unknown Token",
            base_token_symbol=self.symbol or "UNK",
            base_token_address=self.token_address or "unknown",
            price_data=price_data,
            liquidity_data=liquidity_data,
            volume_data=volume_data,
            fdv=self.market_cap,
            created_at=self.timestamp,
        )

    def to_ohlc(self, timeframe: str = "1m") -> Optional[OHLCData]:
        """Convert to OHLC format with real extracted data."""
        if self.price is not None and self.volume_24h is not None:
            return OHLCData(
                timestamp=self.timestamp or int(time.time()),
                open=self.price,
                high=self.price * 1.02,  # Simulate 2% high
                low=self.price * 0.98,  # Simulate 2% low
                close=self.price,
                volume=self.volume_24h,
            )
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            # Trading Data
            "price": self.price,
            "volume_24h": self.volume_24h,
            "txns_24h": self.txns_24h,
            "makers": self.makers,
            "liquidity": self.liquidity,
            "market_cap": self.market_cap,
            # Identification
            "symbol": self.symbol,
            "token_name": self.token_name,
            "chain": self.chain,
            "protocol": self.protocol,
            "age": self.age,
            "boost": self.boost,
            # Addresses
            "pair_address": self.pair_address,
            "creator_address": self.creator_address,
            "token_address": self.token_address,
            "quote_address": self.quote_address,
            # Social/Web
            "website": self.website,
            "twitter": self.twitter,
            "telegram": self.telegram,
            # Changes
            "change_5m": self.change_5m,
            "change_1h": self.change_1h,
            "change_6h": self.change_6h,
            "change_24h": self.change_24h,
            # Metrics
            "confidence_score": self.confidence_score,
            "field_count": self.field_count,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    def is_complete(self, min_fields: int = 5) -> bool:
        """Check if profile has minimum required fields."""
        return self.field_count >= min_fields and self.confidence_score >= 0.3

    def get_display_name(self) -> str:
        """Get best available display name."""
        return (
            self.token_name
            or self.symbol
            or f"Token_{self.record_position or 'Unknown'}"
        )


@dataclass
class ExtractedTokenBatch:
    """Batch of extracted tokens with metadata."""

    tokens: list[TokenProfile] = field(default_factory=list)
    extraction_timestamp: int = field(default_factory=lambda: int(time.time()))
    total_extracted: int = 0
    high_confidence_count: int = 0
    complete_profiles_count: int = 0

    def __post_init__(self):
        """Calculate batch statistics."""
        self.total_extracted = len(self.tokens)
        self.high_confidence_count = len(
            [t for t in self.tokens if t.confidence_score >= 0.7]
        )
        self.complete_profiles_count = len([t for t in self.tokens if t.is_complete()])

    def get_top_tokens(self, count: int = 10) -> list[TokenProfile]:
        """Get top tokens by confidence and completeness."""
        return sorted(
            self.tokens, key=lambda t: (t.confidence_score, t.field_count), reverse=True
        )[:count]

    def to_trading_pairs(self) -> list[TradingPair]:
        """Convert all tokens to legacy TradingPair format."""
        return [token.to_trading_pair() for token in self.tokens]

    def to_ohlc_batch(self, timeframe: str = "1m") -> list[OHLCData]:
        """Convert all tokens to OHLC format."""
        ohlc_data = []
        for token in self.tokens:
            ohlc = token.to_ohlc(timeframe)
            if ohlc:
                ohlc_data.append(ohlc)
        return ohlc_data

    def export_csv(self, filename: str, format_type: str = "ohlcv") -> str:
        """Export batch to CSV file with specified format.

        Args:
            filename: Output CSV filename
            format_type: Format type - "ohlcv" or "ohlcvt"

        Returns:
            Filename of exported file
        """
        ohlc_data = self.to_ohlc_batch()

        with open(filename, "w", newline="") as csvfile:
            if format_type == "ohlcvt":
                csvfile.write("DateTime,Open,High,Low,Close,Volume,Trades\n")
                for ohlc in ohlc_data:
                    csvfile.write(ohlc.to_ohlcvt_format() + "\n")
            else:  # Default OHLCV
                csvfile.write("DateTime,Open,High,Low,Close,Volume\n")
                for ohlc in ohlc_data:
                    csvfile.write(ohlc.to_csv_format() + "\n")

        return filename

    def export_mt5(self, filename: str) -> str:
        """Export batch to MT5 format file.

        Args:
            filename: Output MT5 filename

        Returns:
            Filename of exported file
        """
        ohlc_data = self.to_ohlc_batch()

        with open(filename, "w") as mt5file:
            for ohlc in ohlc_data:
                mt5file.write(ohlc.to_mt5_format() + "\n")

        return filename

    def to_csv_string(self, format_type: str = "ohlcv") -> str:
        """Export batch to CSV string format.

        Args:
            format_type: Format type - "ohlcv" or "ohlcvt"

        Returns:
            CSV formatted string
        """
        output = StringIO()
        ohlc_data = self.to_ohlc_batch()

        if format_type == "ohlcvt":
            output.write("DateTime,Open,High,Low,Close,Volume,Trades\n")
            for ohlc in ohlc_data:
                output.write(ohlc.to_ohlcvt_format() + "\n")
        else:  # Default OHLCV
            output.write("DateTime,Open,High,Low,Close,Volume\n")
            for ohlc in ohlc_data:
                output.write(ohlc.to_csv_format() + "\n")

        result = output.getvalue()
        output.close()
        return result


class TradingViewExporter:
    """Export data in TradingView format."""

    @staticmethod
    def format_ohlcv(ohlc_data: List[OHLCData]) -> str:
        """Format OHLC data for TradingView charting library.

        Args:
            ohlc_data: List of OHLC data points

        Returns:
            TradingView formatted JSON string
        """
        import json

        tv_data = {
            "s": "ok",
            "t": [int(ohlc.timestamp) for ohlc in ohlc_data],
            "o": [ohlc.open for ohlc in ohlc_data],
            "h": [ohlc.high for ohlc in ohlc_data],
            "l": [ohlc.low for ohlc in ohlc_data],
            "c": [ohlc.close for ohlc in ohlc_data],
            "v": [ohlc.volume for ohlc in ohlc_data],
        }

        return json.dumps(tv_data, separators=(",", ":"))


class BinanceExporter:
    """Export data in Binance API format."""

    @staticmethod
    def format_klines(ohlc_data: List[OHLCData]) -> str:
        """Format OHLC data like Binance klines API.

        Args:
            ohlc_data: List of OHLC data points

        Returns:
            Binance klines formatted JSON string
        """
        import json

        klines = []
        for ohlc in ohlc_data:
            kline = [
                int(ohlc.timestamp * 1000),  # Open time (milliseconds)
                f"{ohlc.open:.8f}",  # Open price
                f"{ohlc.high:.8f}",  # High price
                f"{ohlc.low:.8f}",  # Low price
                f"{ohlc.close:.8f}",  # Close price
                f"{ohlc.volume:.8f}",  # Volume
                int(ohlc.timestamp * 1000) + 60000,  # Close time (assume 1m candles)
                f"{ohlc.volume:.8f}",  # Quote asset volume
                ohlc.trades if ohlc.trades else 1,  # Number of trades
                f"{ohlc.volume * 0.6:.8f}",  # Taker buy base asset volume
                f"{ohlc.volume * 0.6:.8f}",  # Taker buy quote asset volume
                "0",  # Unused field
            ]
            klines.append(kline)

        return json.dumps(klines, separators=(",", ":"))


class CoinGeckoExporter:
    """Export data in CoinGecko API format."""

    @staticmethod
    def format_market_data(tokens: List[TokenProfile]) -> str:
        """Format token data like CoinGecko market data API.

        Args:
            tokens: List of token profiles

        Returns:
            CoinGecko formatted JSON string
        """
        import json

        market_data = []
        for i, token in enumerate(tokens):
            if not token.price:
                continue

            entry = {
                "id": f"token-{i}",
                "symbol": token.symbol or f"token{i}",
                "name": token.token_name or token.symbol or f"Token {i}",
                "current_price": token.price,
                "market_cap": token.market_cap,
                "total_volume": token.volume_24h,
                "price_change_percentage_24h": token.change_24h,
                "price_change_percentage_1h_in_currency": token.change_1h,
                "price_change_percentage_24h_in_currency": token.change_24h,
                "market_cap_rank": i + 1,
                "circulating_supply": None,
                "total_supply": None,
                "max_supply": None,
                "ath": token.price * 1.2,  # Estimate ATH
                "ath_change_percentage": -16.67,  # Estimate
                "last_updated": datetime.fromtimestamp(
                    token.timestamp or time.time()
                ).isoformat(),
            }
            market_data.append(entry)

        return json.dumps(market_data, separators=(",", ":"), default=str)


class PancakeSwapExporter:
    """Export data in PancakeSwap format."""

    @staticmethod
    def format_tokens(tokens: List[TokenProfile]) -> str:
        """Format token data for PancakeSwap-style APIs.

        Args:
            tokens: List of token profiles

        Returns:
            PancakeSwap formatted JSON string
        """
        import json

        pancake_data = {}
        for token in tokens:
            if not token.token_address or not token.price:
                continue

            pancake_data[token.token_address] = {
                "name": token.token_name or token.symbol,
                "symbol": token.symbol,
                "price": str(token.price),
                "price_BNB": str(token.price * 0.002),  # Estimate BNB price
                "updated_at": int(token.timestamp or time.time()),
            }

        return json.dumps(pancake_data, separators=(",", ":"))


class ExcelExporter:
    """Export data to Excel-compatible formats."""

    @staticmethod
    def format_tokens_csv(tokens: List[TokenProfile]) -> str:
        """Format tokens for Excel import.

        Args:
            tokens: List of token profiles

        Returns:
            Excel-compatible CSV string
        """
        import csv

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Symbol",
                "Name",
                "Price",
                "Volume_24h",
                "Market_Cap",
                "Transactions_24h",
                "Makers",
                "Liquidity",
                "Change_24h",
                "Confidence",
                "Website",
                "Twitter",
                "Timestamp",
            ]
        )

        # Data rows
        for token in tokens:
            writer.writerow(
                [
                    token.symbol or "",
                    token.token_name or "",
                    token.price or "",
                    token.volume_24h or "",
                    token.market_cap or "",
                    token.txns_24h or "",
                    token.makers or "",
                    token.liquidity or "",
                    token.change_24h or "",
                    token.confidence_score,
                    token.website or "",
                    token.twitter or "",
                    format_timestamp(token.timestamp),
                ]
            )

        result = output.getvalue()
        output.close()
        return result


class JsonLinesExporter:
    """Export data in JSON Lines format."""

    @staticmethod
    def format_tokens(tokens: List[TokenProfile]) -> str:
        """Format tokens as JSON Lines (JSONL).

        Args:
            tokens: List of token profiles

        Returns:
            JSON Lines formatted string
        """
        lines = []
        for token in tokens:
            lines.append(token.to_json())
        return "\n".join(lines)

    @staticmethod
    def format_ohlc(ohlc_data: List[OHLCData]) -> str:
        """Format OHLC data as JSON Lines.

        Args:
            ohlc_data: List of OHLC data points

        Returns:
            JSON Lines formatted string
        """
        import json

        lines = []
        for ohlc in ohlc_data:
            lines.append(json.dumps(ohlc.to_dict(), separators=(",", ":"), default=str))
        return "\n".join(lines)


class PrometheusExporter:
    """Export metrics in Prometheus format."""

    @staticmethod
    def format_metrics(batch: ExtractedTokenBatch) -> str:
        """Format batch data as Prometheus metrics.

        Args:
            batch: Token batch to export

        Returns:
            Prometheus metrics format string
        """
        lines = []
        timestamp_ms = batch.extraction_timestamp * 1000

        # Batch-level metrics
        lines.append(f"# HELP dex_tokens_extracted_total Total tokens extracted")
        lines.append(f"# TYPE dex_tokens_extracted_total counter")
        lines.append(
            f"dex_tokens_extracted_total {batch.total_extracted} {timestamp_ms}"
        )

        lines.append(
            f"# HELP dex_tokens_high_confidence High confidence tokens extracted"
        )
        lines.append(f"# TYPE dex_tokens_high_confidence gauge")
        lines.append(
            f"dex_tokens_high_confidence {batch.high_confidence_count} {timestamp_ms}"
        )

        # Token-level metrics
        lines.append(f"# HELP dex_token_price Token price in USD")
        lines.append(f"# TYPE dex_token_price gauge")

        lines.append(f"# HELP dex_token_volume_24h Token 24h volume in USD")
        lines.append(f"# TYPE dex_token_volume_24h gauge")

        for token in batch.get_top_tokens(10):
            symbol = token.symbol or f"token_{batch.tokens.index(token)}"

            if token.price:
                lines.append(
                    f'dex_token_price{{symbol="{symbol}"}} {token.price} {timestamp_ms}'
                )

            if token.volume_24h:
                lines.append(
                    f'dex_token_volume_24h{{symbol="{symbol}"}} {token.volume_24h} {timestamp_ms}'
                )

        return "\n".join(lines) + "\n"


def format_timestamp(timestamp: Optional[int]) -> str:
    """Format timestamp for display."""
    if timestamp is None:
        return ""

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
