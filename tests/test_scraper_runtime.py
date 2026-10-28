"""Characterization tests for DexScraper's connection, streaming and output paths.

They pin the current resilience contract: which failures are swallowed, what is
logged or printed, and when the loops stop. Network calls and sleeps are faked.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper import DexScraper
from dexscraper.models import ExtractedTokenBatch, TokenProfile, TradingPair


class _StopLoop(BaseException):
    """Raised from a faked sleep to end an otherwise infinite loop."""


def _profile(symbol: str = "PEPE") -> TokenProfile:
    return TokenProfile(
        symbol=symbol,
        price=0.0025,
        volume_24h=250_000.0,
        liquidity=50_000.0,
        market_cap=2_000_000.0,
        confidence_score=0.9,
        field_count=4,
        timestamp=1_700_000_000,
    )


def _websocket(*messages: Any) -> Mock:
    websocket = Mock()
    websocket.recv = AsyncMock(side_effect=list(messages))
    websocket.close = AsyncMock()
    return websocket


class TestExtractTokenData:
    async def test_no_connection_returns_empty_batch(self) -> None:
        scraper = DexScraper()
        with patch.object(scraper, "_connect", new=AsyncMock(return_value=None)):
            batch = await scraper.extract_token_data()
        assert batch.tokens == []

    async def test_text_frames_are_encoded_before_parsing(self) -> None:
        scraper = DexScraper()
        websocket = _websocket("hello", "xxpairs" + "A" * 40)
        extract = AsyncMock(return_value=[_profile()])
        with (
            patch.object(scraper, "_connect", new=AsyncMock(return_value=websocket)),
            patch.object(scraper, "_extract_all_tokens", new=extract),
        ):
            batch = await scraper.extract_token_data()
        data, data_start = extract.await_args.args
        assert data_start == 2 + 20
        assert data == b"A" * 25
        assert [t.symbol for t in batch.tokens] == ["PEPE"]
        websocket.close.assert_awaited_once()

    async def test_missing_pairs_section_returns_empty_batch(self) -> None:
        scraper = DexScraper()
        websocket = _websocket(b"hello", b"no section here")
        with patch.object(scraper, "_connect", new=AsyncMock(return_value=websocket)):
            batch = await scraper.extract_token_data()
        assert batch.tokens == []
        websocket.close.assert_awaited_once()

    async def test_errors_while_reading_are_swallowed_and_socket_closed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        scraper = DexScraper()
        websocket = _websocket(b"hello", RuntimeError("boom"))
        with patch.object(scraper, "_connect", new=AsyncMock(return_value=websocket)):
            batch = await scraper.extract_token_data()
        assert batch.tokens == []
        assert "Error during extraction: boom" in caplog.text
        websocket.close.assert_awaited_once()

    async def test_real_extraction_on_synthetic_message(self) -> None:
        from tests.test_scraper_characterization import build_corpus

        scraper = DexScraper()
        websocket = _websocket(b"hello", build_corpus(42, 8))
        with patch.object(scraper, "_connect", new=AsyncMock(return_value=websocket)):
            batch = await scraper.extract_token_data()
        assert batch.tokens
        assert all(token.symbol for token in batch.tokens)


class TestConnect:
    async def test_cloudflare_bypass_headers_and_cookie_are_used(self) -> None:
        scraper = DexScraper()
        bypass = Mock()
        bypass.prepare_websocket_connection = AsyncMock(
            return_value={"cookie_header": "cf=1", "user_agent": "UA/1"}
        )
        bypass.get_enhanced_headers = Mock(side_effect=lambda h: {**h, "X-CF": "1"})
        scraper.cf_bypass = bypass
        with (
            patch("dexscraper.scraper._CONNECT_HEADERS_PARAM", "additional_headers"),
            patch("websockets.connect", new_callable=AsyncMock) as connect,
        ):
            await scraper._connect()
        headers = connect.await_args.kwargs["additional_headers"]
        assert headers["Cookie"] == "cf=1"
        assert headers["User-Agent"] == "UA/1"
        assert headers["X-CF"] == "1"
        assert "Origin" not in headers

    async def test_gives_up_after_max_retries(self) -> None:
        scraper = DexScraper(max_retries=3)
        with (
            patch("websockets.connect", side_effect=OSError("refused")) as connect,
            patch("dexscraper.scraper.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            assert await scraper._connect() is None
        assert connect.call_count == 3
        backoffs = [c.args[0] for c in sleep.await_args_list if c.args[0] > 0.5]
        assert len(backoffs) == 2  # between attempts, none after the last one
        assert scraper._retry_count == 3

    async def test_proxy_ignored_when_websockets_lacks_support(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("DEXSCRAPER_PROXY", "http://proxy:8080")
        scraper = DexScraper()
        with (
            patch("dexscraper.scraper._CONNECT_SUPPORTS_PROXY", False),
            patch("websockets.connect", new_callable=AsyncMock) as connect,
        ):
            await scraper._connect()
        assert "proxy" not in connect.await_args.kwargs
        assert "doesn't support proxy overrides" in caplog.text


class TestStreaming:
    async def test_enhanced_batches_go_to_callback(self) -> None:
        scraper = DexScraper()
        batch = ExtractedTokenBatch(tokens=[_profile()])
        received: list[Any] = []
        with (
            patch.object(
                scraper, "extract_token_data", new=AsyncMock(return_value=batch)
            ),
            patch(
                "dexscraper.scraper.asyncio.sleep", new=AsyncMock(side_effect=_StopLoop)
            ),
            pytest.raises(_StopLoop),
        ):
            await scraper.stream_pairs(callback=received.append)
        assert received == [batch]

    async def test_legacy_pairs_go_to_callback(self) -> None:
        scraper = DexScraper()
        pairs = [_profile().to_trading_pair()]
        received: list[Any] = []
        with (
            patch.object(scraper, "get_pairs_once", new=AsyncMock(return_value=pairs)),
            patch(
                "dexscraper.scraper.asyncio.sleep", new=AsyncMock(side_effect=_StopLoop)
            ),
            pytest.raises(_StopLoop),
        ):
            await scraper.stream_pairs(
                callback=received.append, use_enhanced_extraction=False
            )
        assert received == [pairs]

    async def test_without_callback_prints_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        scraper = DexScraper()
        batch = ExtractedTokenBatch(tokens=[_profile()])
        with (
            patch.object(
                scraper, "extract_token_data", new=AsyncMock(return_value=batch)
            ),
            patch(
                "dexscraper.scraper.asyncio.sleep", new=AsyncMock(side_effect=_StopLoop)
            ),
            pytest.raises(_StopLoop),
        ):
            await scraper.stream_pairs()
        assert json.loads(capsys.readouterr().out)["type"] == "enhanced_tokens"

    async def test_errors_back_off_ten_seconds_and_continue(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        scraper = DexScraper()
        sleep = AsyncMock(side_effect=[None, _StopLoop()])
        with (
            patch.object(
                scraper,
                "extract_token_data",
                new=AsyncMock(side_effect=ValueError("x")),
            ),
            patch("dexscraper.scraper.asyncio.sleep", new=sleep),
            pytest.raises(_StopLoop),
        ):
            await scraper.stream_pairs()
        assert [c.args[0] for c in sleep.await_args_list] == [10, 10]
        assert "Error in streaming: x" in caplog.text

    async def test_keyboard_interrupt_stops_the_stream(self) -> None:
        scraper = DexScraper()
        with patch.object(
            scraper, "extract_token_data", new=AsyncMock(side_effect=KeyboardInterrupt)
        ):
            await scraper.stream_pairs()

    async def test_get_pairs_once(self) -> None:
        scraper = DexScraper()
        with patch.object(
            scraper,
            "extract_token_data",
            new=AsyncMock(return_value=ExtractedTokenBatch(tokens=[_profile()])),
        ):
            pairs = await scraper.get_pairs_once()
        assert pairs is not None
        assert isinstance(pairs[0], TradingPair)
        with patch.object(
            scraper,
            "extract_token_data",
            new=AsyncMock(return_value=ExtractedTokenBatch()),
        ):
            assert await scraper.get_pairs_once() is None


class TestRun:
    async def test_run_streams_with_requested_options(self) -> None:
        scraper = DexScraper()
        with patch.object(scraper, "stream_pairs", new=AsyncMock()) as stream:
            await scraper.run(output_format="ohlc", use_enhanced_extraction=False)
        stream.assert_awaited_once_with(
            output_format="ohlc", use_enhanced_extraction=False
        )

    @pytest.mark.parametrize("error", [KeyboardInterrupt(), RuntimeError("bad")])
    async def test_run_swallows_interrupts_and_errors(
        self, error: BaseException, caplog: pytest.LogCaptureFixture
    ) -> None:
        scraper = DexScraper()
        with patch.object(scraper, "stream_pairs", new=AsyncMock(side_effect=error)):
            await scraper.run()
        if isinstance(error, RuntimeError):
            assert "Enhanced scraper error: bad" in caplog.text


class TestOutput:
    async def test_enhanced_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        batch = ExtractedTokenBatch(tokens=[_profile("A"), _profile("B")])
        await DexScraper()._output_enhanced_batch(batch, "json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["type"] == "enhanced_tokens"
        assert payload["total_extracted"] == 2
        assert [t["symbol"] for t in payload["tokens"]] == ["A", "B"]

    @pytest.mark.parametrize("fmt", ["ohlc", "mt5"])
    async def test_enhanced_ohlc_formats(
        self, fmt: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        batch = ExtractedTokenBatch(tokens=[_profile()])
        await DexScraper()._output_enhanced_batch(batch, fmt)
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1
        if fmt == "ohlc":
            assert lines[0].startswith("TOKEN,1700000000,0.0025,")
        else:
            assert lines[0] == batch.to_ohlc_batch()[0].to_mt5_format()

    async def test_unknown_format_prints_nothing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        batch = ExtractedTokenBatch(tokens=[_profile()])
        await DexScraper()._output_enhanced_batch(batch, "csv")
        await DexScraper()._output_pairs([_profile().to_trading_pair()], "csv")
        assert capsys.readouterr().out == ""

    async def test_pairs_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        pair = _profile().to_trading_pair()
        await DexScraper()._output_pairs([pair], "json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["type"] == "pairs"
        assert payload["pairs"] == [pair.to_dict()]

    @pytest.mark.parametrize("fmt", ["ohlc", "mt5"])
    async def test_pairs_ohlc_formats(
        self, fmt: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        priced = _profile().to_trading_pair()
        unpriced = TradingPair(
            chain="solana",
            protocol="x",
            pair_address="p",
            base_token_name="n",
            base_token_symbol="NOPE",
            base_token_address="a",
        )
        await DexScraper()._output_pairs([priced, unpriced], fmt)
        lines = capsys.readouterr().out.splitlines()
        ohlc = priced.to_ohlc()
        assert ohlc is not None
        # Pairs without price data still print, with TradingPair's 1.0 defaults.
        assert len(lines) == 2
        if fmt == "ohlc":
            assert lines[0] == (
                f"PEPE,{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},"
                f"{ohlc.close},{ohlc.volume}"
            )
            assert lines[1].startswith("NOPE,")
            assert lines[1].endswith(",1.0,1.0,1.0,1.0,1000.0")
        else:
            assert lines[0] == ohlc.to_mt5_format()
            assert lines[1].endswith(
                ",1.00000000,1.00000000,1.00000000,1.00000000,1000"
            )


@pytest.mark.parametrize(
    ("distance", "expect_age", "expect_protocol"),
    [
        (180, "5m", "pumpfun"),
        (181, None, "pumpfun"),
        (220, None, "pumpfun"),
        (221, None, "unknown"),
    ],
)
def test_enrich_distance_gates(
    distance: int, expect_age: str | None, expect_protocol: str
) -> None:
    profile = TokenProfile(symbol="X", timestamp=1)
    metadata: dict[str, list[dict[str, Any]]] = {
        "age_indicators": [{"age": "5m", "position": 1000 + distance}],
        "protocols": [{"protocol": "pumpfun", "position": 1000 + distance}],
    }
    DexScraper()._enrich_token_profile(profile, "X", 1000, metadata)
    assert profile.age == expect_age
    assert profile.protocol == expect_protocol
