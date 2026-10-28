"""Unit tests for the binary protocol decoders (protocol.py, enhanced_protocol.py)."""

import math
import struct

import pytest

from dexscraper import enhanced_protocol, protocol
from dexscraper.enhanced_protocol import EnhancedProtocolParser, parse_message_enhanced
from dexscraper.protocol import (
    decode_metrics,
    decode_pair,
    decode_pair_from_text,
    handle_double,
    parse_message,
    parse_variable_length,
)

HEADER = b"\x00\n1.3.0\n"
SOL_TOKEN = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
SOL_PAIR = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"


def _field(text: str) -> bytes:
    raw = text.encode()
    return bytes([len(raw)]) + raw


def _binary_pair(timestamp: float = 1_700_000_000.0) -> bytes:
    """A length-prefixed pair record followed by eight aligned doubles."""
    body = b"".join(
        _field(value)
        for value in (
            "ethereum",
            "uniswap",
            "0xpairaddress",
            "Example Token",
            "EXT",
            "0xtokenaddress",
        )
    )
    body += b"\x00" * ((8 - len(body) % 8) % 8)
    metrics = (1.5, 1.25, 2.5, 10_000.0, 5_000.0, 1_000_000.0, timestamp, 0.0)
    return body + struct.pack("8d", *metrics)


class TestHelpers:
    def test_handle_double_rejects_nan_inf_and_non_floats(self) -> None:
        assert handle_double(math.nan) == 0.0
        assert handle_double(math.inf) == 0.0
        assert handle_double(-math.inf) == 0.0
        assert handle_double(3) == 0.0  # type: ignore[arg-type]
        assert handle_double(1.25) == 1.25

    def test_decode_metrics_needs_64_bytes(self) -> None:
        assert decode_metrics(b"\x00" * 63, 0) == ({}, 0)

    def test_decode_metrics_drops_zero_and_nan_values(self) -> None:
        raw = struct.pack("8d", 1.0, 0.0, math.nan, 4.0, 5.0, 6.0, 7.0, 8.0)
        metrics, pos = decode_metrics(raw, 0)
        assert pos == 64
        assert metrics == {
            "price": 1.0,
            "liquidityUsd": 4.0,
            "volumeH24": 5.0,
            "fdv": 6.0,
            "timestamp": 7.0,
        }


class TestDecodePair:
    def test_binary_record_round_trip(self) -> None:
        pair = decode_pair(_binary_pair())
        assert pair is not None
        assert pair.chain == "ethereum"
        assert pair.protocol == "uniswap"
        assert pair.pair_address == "0xpairaddress"
        assert pair.base_token_name == "Example Token"
        assert pair.base_token_symbol == "EXT"
        assert pair.base_token_address == "0xtokenaddress"
        assert pair.price_data is not None
        assert pair.price_data.current == 1.5
        assert pair.price_data.usd == 1.25
        assert pair.price_data.change_24h == 2.5
        assert pair.liquidity_data is not None and pair.liquidity_data.usd == 10_000.0
        assert pair.volume_data is not None and pair.volume_data.h24 == 5_000.0
        assert pair.fdv == 1_000_000.0
        assert pair.created_at == 1_700_000_000
        assert pair.created_at_formatted

    def test_out_of_range_timestamp_is_ignored(self) -> None:
        pair = decode_pair(_binary_pair(timestamp=9e12))
        assert pair is not None
        assert pair.created_at is None
        assert pair.created_at_formatted is None

    def test_too_few_fields_returns_none(self) -> None:
        data = _field("ethereum") + _field("uniswap") + b"\x00" * 6
        data += struct.pack("8d", 1.0, 1.0, 0, 0, 0, 0, 0, 0)
        assert decode_pair(data) is None

    def test_record_without_meaningful_metrics_returns_none(self) -> None:
        body = b"".join(_field(v) for v in ("ethereum", "uniswap", "0xpair", "Tok"))
        body += b"\x00" * ((8 - len(body) % 8) % 8)
        body += struct.pack("8d", 0, 0, 0, 0, 0, 0, 5.0, 0)
        assert decode_pair(body) is None

    def test_text_records_use_text_decoder(self) -> None:
        data = f"solana raydium BONK BonkInuToken {SOL_TOKEN} {SOL_PAIR}".encode()
        pair = decode_pair(data)
        assert pair is not None
        assert pair.chain == "solana"
        assert pair.protocol == "raydium"
        assert pair.base_token_symbol == "BONK"
        assert pair.base_token_address == SOL_TOKEN
        assert pair.pair_address == SOL_PAIR


class TestDecodePairFromText:
    def test_needs_three_words(self) -> None:
        assert decode_pair_from_text(b"ab cd") is None

    def test_skips_social_words_for_names(self) -> None:
        pair = decode_pair_from_text(b"twitter telegram MEME MemeCoinName orca")
        assert pair is not None
        assert pair.base_token_name == "MemeCoinName"
        assert pair.base_token_symbol == "MEME"
        assert pair.protocol == "orca"

    def test_unknown_protocol_default(self) -> None:
        pair = decode_pair_from_text(b"xx MEME MemeCoinName")
        assert pair is not None
        assert pair.protocol == "unknown"

    def test_nothing_meaningful_returns_none(self) -> None:
        assert decode_pair_from_text(b"12 34 56 78") is None


class TestParseVariableLength:
    def test_splits_sections_on_solana(self) -> None:
        data = (
            f"xx solana raydium BONK BonkInuToken {SOL_TOKEN} {SOL_PAIR} "
            "solana meteora WIF DogWifHatToken"
        ).encode()
        pairs = parse_variable_length(data)
        assert [p.base_token_symbol for p in pairs] == ["BONK", "WIF"]
        assert pairs[0].protocol == "raydium"
        assert pairs[0].base_token_address == SOL_TOKEN
        assert pairs[0].pair_address == SOL_PAIR
        assert pairs[1].protocol == "meteora"

    def test_skips_short_sections(self) -> None:
        assert parse_variable_length(b"solana tiny solana  ") == []

    def test_caps_at_fifty_pairs(self) -> None:
        data = b" ".join(b"solana raydium TOK LongTokenName" for _ in range(60))
        assert len(parse_variable_length(data)) == 50


class TestParseMessageFallback:
    @pytest.fixture(autouse=True)
    def _no_enhanced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(enhanced_protocol, "parse_message_enhanced", lambda _: [])

    def test_requires_protocol_header(self) -> None:
        assert parse_message(b"not a dexscreener frame") == []

    def test_requires_pairs_section(self) -> None:
        assert parse_message(HEADER + b"nothing here") == []

    def test_fixed_chunks_decode_binary_pairs(self) -> None:
        record = _binary_pair()
        chunk = record + b"\xff" * (128 - len(record))
        message = HEADER + b"pairs" + b"\x00" * 4 + chunk * 3 + b"\xff" * 128
        pairs = parse_message(message)
        assert len(pairs) >= 3
        assert all(p.base_token_symbol == "EXT" for p in pairs)

    def test_falls_back_to_variable_length(self) -> None:
        message = HEADER + b"pairs" + b"\x00" * 4 + b"solana raydium BONK BonkInuToken"
        pairs = parse_message(message)
        assert [p.base_token_symbol for p in pairs] == ["BONK"]

    def test_enhanced_errors_fall_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(_: bytes) -> list:
            raise ValueError("bad frame")

        monkeypatch.setattr(enhanced_protocol, "parse_message_enhanced", boom)
        message = HEADER + b"pairs" + b"\x00" * 4 + b"solana raydium BONK BonkInuToken"
        assert [p.base_token_symbol for p in parse_message(message)] == ["BONK"]


def test_parse_message_prefers_enhanced_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = decode_pair(_binary_pair())
    assert sentinel is not None
    monkeypatch.setattr(
        enhanced_protocol, "parse_message_enhanced", lambda _: [sentinel]
    )
    assert protocol.parse_message(b"anything") == [sentinel]


def _cluster_message(text: bytes = b"solana raydium BONK BonkInuToken ") -> bytes:
    numbers = struct.pack("<ddd", 0.0005, 5_000.0, 20.0)
    # the parser scans doubles on 4-byte steps, so keep them aligned
    record = text + b"\x00" * (48 - len(text)) + numbers
    record += b"\x00" * (256 - len(record))
    return b"\x00\n1.3.0\npairs" + b"\x00" * 12 + record * 2


class TestEnhancedParser:
    def test_no_pairs_section(self) -> None:
        assert parse_message_enhanced(b"\x00" * 300) == []

    def test_small_data_section(self) -> None:
        assert parse_message_enhanced(b"pairs" + b"\x00" * 100) == []

    def test_numeric_cluster_becomes_pair(self) -> None:
        pairs = parse_message_enhanced(_cluster_message())
        assert pairs
        pair = pairs[0]
        assert pair.chain == "solana"
        assert pair.protocol == "raydium"
        assert pair.base_token_symbol == "BONK"
        assert pair.price_data is not None
        assert pair.price_data.current == pytest.approx(0.0005)
        assert pair.volume_data is not None
        assert pair.volume_data.h24 == pytest.approx(5_000.0)
        assert pair.created_at is not None

    def test_extract_numeric_categorises_values(self) -> None:
        window = struct.pack("<ddddd", 0.0005, 5_000.0, 20.0, -50.0, 1e12)
        window += b"\x00" * (128 - len(window))
        data = EnhancedProtocolParser()._extract_numeric_from_window(window)
        assert (0, 0.0005) in data["prices"]
        assert (8, 5_000.0) in data["volumes"]
        assert (16, 20.0) in data["counts"]
        assert (24, -50.0) in data["percentages"]
        assert all(v != 1e12 for values in data.values() for _, v in values)

    def test_deduplicate_keeps_richest_non_overlapping(self) -> None:
        parser = EnhancedProtocolParser()
        rich = (0, {"prices": [(0, 0.0005)] * 3, "volumes": [], "counts": []})
        poor = (64, {"prices": [(0, 0.0005)], "volumes": [], "counts": []})
        far = (512, {"prices": [(0, 0.0005)], "volumes": [], "counts": []})
        assert parser._deduplicate_clusters([poor, rich, far]) == [rich, far]
        assert parser._deduplicate_clusters([]) == []

    def test_text_fallback_when_no_clusters(self) -> None:
        text = b"solana raydium BONK BonkInuToken"
        message = b"pairs" + b"\x00" * 12 + text + b"\x00" * (200 - len(text))
        pairs = parse_message_enhanced(message)
        assert [p.base_token_symbol for p in pairs] == ["BONK"]

    def test_parse_errors_are_contained(self, monkeypatch: pytest.MonkeyPatch) -> None:
        parser = EnhancedProtocolParser()

        def boom(_: bytes) -> list:
            raise ValueError("bad")

        monkeypatch.setattr(parser, "_extract_trading_pairs", boom)
        assert parser.parse_message(b"pairs" + b"\x00" * 200) == []
