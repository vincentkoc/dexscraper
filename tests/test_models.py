#!/usr/bin/env python3
"""Test cases for dexscraper models and data export functionality."""

import time
from datetime import datetime

import pytest

from dexscraper.models import ExtractedTokenBatch, OHLCData, TokenProfile


class TestOHLCData:
    """Test OHLC data formatting and exports."""

    def setup_method(self):
        """Setup test data."""
        self.timestamp = int(time.time())
        self.ohlc = OHLCData(
            timestamp=self.timestamp,
            open=0.000123,
            high=0.000127,
            low=0.000119,
            close=0.000125,
            volume=1000000.50,
            trades=150,
        )

    def test_mt5_format(self):
        """Test MT5 format output."""
        result = self.ohlc.to_mt5_format()
        dt = datetime.fromtimestamp(self.timestamp)
        expected = f"{dt.strftime('%Y.%m.%d %H:%M:%S')},0.00012300,0.00012700,0.00011900,0.00012500,1000000"
        assert result == expected

    def test_csv_format(self):
        """Test CSV format output."""
        result = self.ohlc.to_csv_format()
        dt = datetime.fromtimestamp(self.timestamp)
        expected = f"{dt.strftime('%Y-%m-%d %H:%M:%S')},0.00012300,0.00012700,0.00011900,0.00012500,1000000.50"
        assert result == expected

    def test_ohlcvt_format(self):
        """Test OHLCVT format output."""
        result = self.ohlc.to_ohlcvt_format()
        dt = datetime.fromtimestamp(self.timestamp)
        expected = f"{dt.strftime('%Y-%m-%d %H:%M:%S')},0.00012300,0.00012700,0.00011900,0.00012500,1000000.50,150"
        assert result == expected

    def test_ohlcvt_format_no_trades(self):
        """Test OHLCVT format with estimated trades."""
        ohlc_no_trades = OHLCData(
            timestamp=self.timestamp,
            open=0.000123,
            high=0.000127,
            low=0.000119,
            close=0.000125,
            volume=1000000.50,
        )
        result = ohlc_no_trades.to_ohlcvt_format()
        dt = datetime.fromtimestamp(self.timestamp)
        expected = f"{dt.strftime('%Y-%m-%d %H:%M:%S')},0.00012300,0.00012700,0.00011900,0.00012500,1000000.50,1000"
        assert result == expected

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = self.ohlc.to_dict()
        expected_keys = {
            "timestamp",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "trades",
        }
        assert set(result.keys()) == expected_keys
        assert result["timestamp"] == self.timestamp
        assert result["open"] == 0.000123
        assert result["trades"] == 150


class TestTokenProfile:
    """Test TokenProfile functionality."""

    def setup_method(self):
        """Setup test token profile."""
        self.token = TokenProfile(
            symbol="TEST",
            price=0.000123,
            volume_24h=1000000.50,
            txns_24h=500,
            makers=25,
            liquidity=50000.0,
            market_cap=5000000.0,
            confidence_score=0.85,
            field_count=8,
            timestamp=int(time.time()),
        )

    def test_to_ohlc(self):
        """Test OHLC conversion."""
        ohlc = self.token.to_ohlc()
        assert ohlc is not None
        assert ohlc.open == self.token.price
        assert ohlc.close == self.token.price
        assert ohlc.volume == self.token.volume_24h
        assert ohlc.high == self.token.price * 1.02
        assert ohlc.low == self.token.price * 0.98

    def test_to_ohlc_no_data(self):
        """Test OHLC conversion with missing data."""
        empty_token = TokenProfile()
        ohlc = empty_token.to_ohlc()
        assert ohlc is None

    def test_is_complete(self):
        """Test completeness check."""
        assert self.token.is_complete()

        incomplete_token = TokenProfile(field_count=2, confidence_score=0.1)
        assert not incomplete_token.is_complete()

    def test_get_display_name(self):
        """Test display name generation."""
        assert self.token.get_display_name() == "TEST"

        token_no_symbol = TokenProfile(token_name="Test Token")
        assert token_no_symbol.get_display_name() == "Test Token"

        empty_token = TokenProfile(record_position=5)
        assert empty_token.get_display_name() == "Token_5"


class TestExtractedTokenBatch:
    """Test batch operations and exports."""

    def setup_method(self):
        """Setup test batch with multiple tokens."""
        self.tokens = [
            TokenProfile(
                symbol=f"TOKEN_{i:02d}",
                price=0.000100 + i * 0.000010,
                volume_24h=1000000 + i * 100000,
                confidence_score=0.7 + i * 0.05,
                field_count=5 + i,
                timestamp=int(time.time()),
            )
            for i in range(5)
        ]
        self.batch = ExtractedTokenBatch(tokens=self.tokens)

    def test_batch_statistics(self):
        """Test batch statistics calculation."""
        assert self.batch.total_extracted == 5
        assert self.batch.high_confidence_count >= 3  # Tokens with score >= 0.7
        assert self.batch.complete_profiles_count == 5  # All have >= 5 fields

    def test_get_top_tokens(self):
        """Test top tokens selection."""
        top_3 = self.batch.get_top_tokens(3)
        assert len(top_3) == 3

        # Should be sorted by confidence and field count (descending)
        for i in range(len(top_3) - 1):
            current = top_3[i]
            next_token = top_3[i + 1]
            assert current.confidence_score >= next_token.confidence_score

    def test_to_ohlc_batch(self):
        """Test batch OHLC conversion."""
        ohlc_data = self.batch.to_ohlc_batch()
        assert len(ohlc_data) == 5

        # All should be valid OHLC data
        for ohlc in ohlc_data:
            assert ohlc.open > 0
            assert ohlc.close > 0
            assert ohlc.volume > 0

    def test_csv_string_export(self):
        """Test CSV string export."""
        # Test OHLCV format
        csv_ohlcv = self.batch.to_csv_string("ohlcv")
        assert "DateTime,Open,High,Low,Close,Volume" in csv_ohlcv
        lines = csv_ohlcv.strip().split("\n")
        assert len(lines) == 6  # Header + 5 data rows

        # Test OHLCVT format
        csv_ohlcvt = self.batch.to_csv_string("ohlcvt")
        assert "DateTime,Open,High,Low,Close,Volume,Trades" in csv_ohlcvt
        lines = csv_ohlcvt.strip().split("\n")
        assert len(lines) == 6  # Header + 5 data rows

    def test_export_csv_file(self, tmp_path):
        """Test CSV file export."""
        csv_file = tmp_path / "test_export.csv"
        result_file = self.batch.export_csv(str(csv_file), "ohlcv")

        assert result_file == str(csv_file)
        assert csv_file.exists()

        # Check file content
        content = csv_file.read_text()
        assert "DateTime,Open,High,Low,Close,Volume" in content
        lines = content.strip().split("\n")
        assert len(lines) == 6  # Header + 5 data rows

    def test_export_mt5_file(self, tmp_path):
        """Test MT5 file export."""
        mt5_file = tmp_path / "test_export.mt5"
        result_file = self.batch.export_mt5(str(mt5_file))

        assert result_file == str(mt5_file)
        assert mt5_file.exists()

        # Check file content
        content = mt5_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 5  # 5 data rows (no header for MT5)

        # Each line should have MT5 format
        for line in lines:
            parts = line.split(",")
            assert len(parts) == 6  # DateTime,Open,High,Low,Close,Volume
            # First part should be datetime in MT5 format (YYYY.MM.DD HH:MM:SS)
            datetime_part = parts[0]
            assert "." in datetime_part and ":" in datetime_part

    def test_to_trading_pairs(self):
        """Test conversion to legacy TradingPair format."""
        trading_pairs = self.batch.to_trading_pairs()
        assert len(trading_pairs) == 5

        for pair in trading_pairs:
            assert pair.chain == "solana"
            assert pair.base_token_symbol.startswith("TOKEN_")
            assert pair.price_data is not None
            assert pair.volume_data is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
