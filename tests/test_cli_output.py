"""Tests for CLI output callbacks, serialisation and main() control flow."""

import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscraper import cli
from dexscraper.cli import (
    SlickCLI,
    build_batch_output,
    cli_main,
    create_callback,
    create_token_callback,
    emit_cloudflare_runtime_warning,
    normalize_legacy_cli_args,
)
from dexscraper.models import (
    ExtractedTokenBatch,
    LiquidityData,
    PriceData,
    TokenProfile,
    TradingPair,
    VolumeData,
)


def _token(symbol: str = "BONK", confidence: float = 0.9) -> TokenProfile:
    return TokenProfile(
        symbol=symbol,
        token_name=f"{symbol} Token",
        price=0.00002,
        volume_24h=1_234_567.0,
        liquidity=250_000.0,
        market_cap=1_500_000_000.0,
        change_24h=12.5,
        txns_24h=4_200,
        makers=900,
        timestamp=1_700_000_000,
        confidence_score=confidence,
        field_count=8,
    )


def _batch(*symbols: str) -> ExtractedTokenBatch:
    return ExtractedTokenBatch(tokens=[_token(s) for s in symbols or ("BONK",)])


def _pair() -> TradingPair:
    return TradingPair(
        chain="solana",
        protocol="raydium",
        pair_address="pair",
        base_token_name="Bonk",
        base_token_symbol="BONK",
        base_token_address="token",
        price_data=PriceData(current=0.5, usd=0.5),
        volume_data=VolumeData(h24=1000.0),
        liquidity_data=LiquidityData(usd=5000.0),
        fdv=10_000.0,
        created_at=1_700_000_000,
    )


class TestNormalizeLegacyArgs:
    def test_passthrough(self) -> None:
        assert normalize_legacy_cli_args([]) == []
        assert normalize_legacy_cli_args(["--once"]) == ["--once"]

    def test_interactive_maps_to_rich(self) -> None:
        assert normalize_legacy_cli_args(["interactive", "--debug"]) == [
            "--format",
            "rich",
            "--debug",
        ]

    @pytest.mark.parametrize("mode", ["trending", "TOP", "gainers", "new", "boosted"])
    def test_mode_subcommands(self, mode: str) -> None:
        assert normalize_legacy_cli_args([mode, "--once"]) == [
            "--mode",
            mode.lower(),
            "--once",
        ]


class TestBuildBatchOutput:
    def test_json_respects_limit(self) -> None:
        payload = json.loads(build_batch_output(_batch("A", "B", "C"), "json", limit=2))
        assert payload["type"] == "enhanced_tokens"
        assert payload["total_extracted"] == 3
        assert len(payload["tokens"]) == 2

    @pytest.mark.parametrize("fmt", ["ohlcv", "ohlcvt"])
    def test_csv_formats(self, fmt: str) -> None:
        out = build_batch_output(_batch("A", "B"), fmt)
        assert out.strip()
        assert len(out.strip().splitlines()) >= 2

    def test_ohlc_and_mt5(self) -> None:
        ohlc = build_batch_output(_batch("A"), "ohlc")
        assert ohlc.startswith("TOKEN,1700000000,")
        assert build_batch_output(_batch("A"), "mt5").strip()

    def test_unknown_format_is_empty(self) -> None:
        assert build_batch_output(_batch("A"), "nope") == ""


class TestCallbacks:
    def test_pair_callback_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        create_callback("json")([_pair()])
        payload = json.loads(capsys.readouterr().out)
        assert payload["type"] == "pairs"
        assert payload["pairs"][0]["baseTokenSymbol"] == "BONK"

    def test_pair_callback_ohlc(self, capsys: pytest.CaptureFixture[str]) -> None:
        create_callback("ohlc")([_pair()])
        assert capsys.readouterr().out.startswith("BONK,1700000000,0.5,")

    def test_pair_callback_mt5(self, capsys: pytest.CaptureFixture[str]) -> None:
        create_callback("mt5")([_pair()])
        assert capsys.readouterr().out.strip()

    def test_pair_callback_rich(self) -> None:
        with patch.object(cli, "Console") as console_cls:
            create_callback("rich")([_pair()])
        console_cls.return_value.print.assert_called_once()

    def test_token_callback_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        create_token_callback("json", limit=1)(_batch("A", "B"))
        payload = json.loads(capsys.readouterr().out)
        assert payload["type"] == "enhanced_tokens"
        assert len(payload["tokens"]) == 1

    @pytest.mark.parametrize("fmt", ["ohlcv", "ohlcvt"])
    def test_token_callback_csv(
        self, fmt: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_token_callback(fmt)(_batch("A"))
        assert capsys.readouterr().out.strip()

    def test_token_callback_text_fallback(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_token_callback("text")(_batch("A"))
        out = capsys.readouterr().out
        assert "Extracted 1 tokens, 1 high-confidence" in out
        assert "$0.00002000" in out

    def test_token_callback_rich(self) -> None:
        with patch.object(cli, "Console") as console_cls:
            create_token_callback("rich")(_batch("A"))
        console_cls.return_value.print.assert_called_once()


class TestSlickCLIRendering:
    def test_format_large_number(self) -> None:
        ui = SlickCLI()
        assert ui.format_large_number(1_500_000_000) == "$1.5B"
        assert ui.format_large_number(2_500_000) == "$2.5M"
        assert ui.format_large_number(3_500) == "$4K"
        assert ui.format_large_number(12) == "$12"

    def test_layout_and_table_render(self) -> None:
        ui = SlickCLI()
        batch = _batch("A", "B")
        assert ui.create_slick_token_table(batch).row_count == 2
        assert ui.create_layout(batch) is not None
        assert ui.create_header_panel() is not None
        assert ui.create_stats_panel(batch) is not None
        assert ui.create_footer_panel(batch) is not None

    def test_display_name_falls_back(self) -> None:
        ui = SlickCLI()
        assert ui.get_token_display_name(TokenProfile(), 3)


class TestEmitCloudflareWarning:
    def test_streaming_is_silent(self, capsys: pytest.CaptureFixture[str]) -> None:
        scraper = Mock()
        emit_cloudflare_runtime_warning(scraper, non_streaming=False)
        scraper.get_cloudflare_runtime_warning.assert_not_called()
        assert capsys.readouterr().err == ""

    def test_once_prints_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        scraper = Mock()
        scraper.get_cloudflare_runtime_warning.return_value = "use --cloudflare-bypass"
        emit_cloudflare_runtime_warning(scraper, non_streaming=True)
        assert "Warning: use --cloudflare-bypass" in capsys.readouterr().err


class TestMain:
    @staticmethod
    def _scraper(batch: ExtractedTokenBatch) -> Mock:
        scraper = Mock()
        scraper.extract_token_data = AsyncMock(return_value=batch)
        scraper.get_cloudflare_runtime_warning.return_value = None
        return scraper

    async def test_once_writes_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "tokens.json"
        argv = ["dexscraper", "--once", "--output", str(out), "--limit", "1"]
        with (
            patch.object(sys, "argv", argv),
            patch.object(
                cli, "DexScraper", return_value=self._scraper(_batch("A", "B"))
            ),
        ):
            await cli.main()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert len(payload["tokens"]) == 1
        assert out.read_text(encoding="utf-8").endswith("\n")

    async def test_once_prints_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with (
            patch.object(sys, "argv", ["dexscraper", "--once"]),
            patch.object(cli, "DexScraper", return_value=self._scraper(_batch("A"))),
        ):
            await cli.main()
        assert json.loads(capsys.readouterr().out)["total_extracted"] == 1

    async def test_once_with_no_tokens_exits_1(self) -> None:
        with (
            patch.object(sys, "argv", ["dexscraper", "--once"]),
            patch.object(
                cli, "DexScraper", return_value=self._scraper(ExtractedTokenBatch())
            ),
            pytest.raises(SystemExit) as exc,
        ):
            await cli.main()
        assert exc.value.code == 1

    async def test_output_without_once_exits_2(self, tmp_path: Path) -> None:
        argv = ["dexscraper", "--output", str(tmp_path / "x.json")]
        with (
            patch.object(sys, "argv", argv),
            patch.object(cli, "DexScraper", return_value=self._scraper(_batch("A"))),
            pytest.raises(SystemExit) as exc,
        ):
            await cli.main()
        assert exc.value.code == 2

    async def test_rich_without_rich_exits_1(self) -> None:
        with (
            patch.object(sys, "argv", ["dexscraper", "--format", "rich"]),
            patch.object(cli, "RICH_AVAILABLE", False),
            pytest.raises(SystemExit) as exc,
        ):
            await cli.main()
        assert exc.value.code == 1

    def test_cli_main_handles_keyboard_interrupt(self) -> None:
        def interrupted(coro: object) -> None:
            coro.close()  # type: ignore[attr-defined]
            raise KeyboardInterrupt

        with (
            patch.object(cli.asyncio, "run", side_effect=interrupted),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 0
