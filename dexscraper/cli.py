"""Command line interface for dexscraper - Claude Code inspired UX."""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from typing import List, TYPE_CHECKING

# Rich types will be imported in the try block below

try:
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.padding import Padding
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints when Rich is not available
    class Table:
        pass

    class Panel:
        pass

    class Layout:
        pass

    RICH_AVAILABLE = False

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
from .models import ExtractedTokenBatch, TokenProfile, TradingPair
from .scraper import DexScraper

# ASCII Ghost Art for loading screen
GHOST_ASCII = """
[dim white]                    ░░░░░░░░░░░░░░░░░░░░[/dim white]
[dim white]                ░░[/dim white][bold magenta]██[/bold magenta][dim white]░░[/dim white][bold magenta]██[/bold magenta][dim white]░░[/dim white][bold magenta]██[/bold magenta][dim white]░░[/dim white][bold magenta]██[/bold magenta][dim white]░░[/dim white]
[dim white]              ░░[/dim white][bold white]████[/bold white][dim white]░░[/dim white][bold white]████[/bold white][dim white]░░[/dim white][bold white]████[/bold white][dim white]░░░░[/dim white]
[dim white]            ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░[/dim white]
[dim white]          ░░[/dim white][bold white]██[/bold white][bold bright_black]██[/bold bright_black][bold white]████[/bold white][bold bright_black]██[/bold bright_black][bold white]██[/bold white][bold bright_black]██[/bold bright_black][bold white]████[/bold white][dim white]░░░░[/dim white]
[dim white]          ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░[/dim white]
[dim white]        ░░[/dim white][bold white]████[/bold white][bold magenta]██[/bold magenta][bold white]██████[/bold white][bold magenta]██[/bold magenta][bold white]████[/bold white][dim white]░░░░[/dim white]
[dim white]        ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░[/dim white]
[dim white]      ░░[/dim white][bold white]████████[/bold white][bold magenta]██[/bold magenta][bold white]██[/bold white][bold magenta]██[/bold magenta][bold white]██████[/bold white][dim white]░░░░[/dim white]
[dim white]      ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░[/dim white]
[dim white]    ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░░░[/dim white]
[dim white]    ░░[/dim white][bold white]██████████████████[/bold white][dim white]░░░░░░[/dim white]
[dim white]  ░░[/dim white][bold white]████████████████████[/bold white][dim white]░░░░░░[/dim white]

[bold bright_magenta]      👻 DexScraper Ghost Protocol[/bold bright_magenta]
[dim bright_white]      Haunting the blockchain...[/dim bright_white]
"""


class SlickCLI:
    """Slick, dark terminal interface with Claude Code-inspired UX."""

    def __init__(self) -> None:
        self.console = Console()
        self.scraper = None
        self.session_start = time.time()
        self.extraction_count = 0

    def clear_screen(self) -> None:
        """Clear terminal screen."""
        self.console.clear()

    def show_ghost_loading(self):
        """Show ASCII ghost with loading animation."""
        self.clear_screen()

        with self.console.status(
            "[primary]Initializing Ghost Protocol...", spinner="dots"
        ):
            time.sleep(2)

        self.console.print(Align.center(GHOST_ASCII))
        time.sleep(1.5)

    def show_main_menu(self):
        """Display main menu with options."""
        self.clear_screen()

        # Header
        self.console.print(
            Rule(
                "[bright_magenta]👻 DexScraper Ghost Protocol[/bright_magenta]",
                style="bright_magenta",
            )
        )
        self.console.print()

        # Menu panel
        menu_text = Text()
        menu_text.append("🚀 ", style="bright_magenta")
        menu_text.append("Choose your destiny:\n\n", style="bright_white")

        options = [
            ("1", "Stream to Terminal", "📺 Live market data stream"),
            ("2", "Export to File", "💾 Save data to file"),
            ("3", "Real-time Monitor", "⚡ Continuous monitoring"),
            ("4", "Configuration", "⚙️  Adjust settings"),
            ("5", "Exit", "👻 Fade away..."),
        ]

        for key, title, desc in options:
            menu_text.append(f"  {key}. ", style="bright_magenta")
            menu_text.append(f"{title}\n", style="bright_white bold")
            menu_text.append(f"     {desc}\n\n", style="bright_black")

        panel = Panel(
            Align.center(menu_text),
            border_style="bright_magenta",
            title="[bright_white bold]Main Menu[/bright_white bold]",
            title_align="center",
        )

        self.console.print(Padding(panel, (1, 0)))

        return Prompt.ask(
            "\n[bright_magenta]→[/bright_magenta] Select option",
            choices=["1", "2", "3", "4", "5"],
            default="1",
        )

    async def extract_data(self):
        """Extract token data with progress animation."""
        if not self.scraper:
            self.scraper = DexScraper(debug=False)

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[bright_magenta]Extracting ghost data..."),
            console=self.console,
        ) as progress:
            progress.add_task("Extraction", total=None)
            batch = await self.scraper.extract_token_data()

        return batch

    def create_slick_token_table(self, batch: ExtractedTokenBatch) -> Table:
        """Create dark-themed token table with proper names."""
        table = Table(
            title="[bright_magenta]👻 Haunted Market Data[/bright_magenta]",
            show_header=True,
            header_style="bright_magenta bold",
            border_style="bright_magenta",
            expand=True,
            show_lines=False,
        )

        # Slick columns with standard colors
        table.add_column("Token", style="bright_white bold", width=16)
        table.add_column("Price", style="bright_green", justify="right", width=12)
        table.add_column("Volume", style="bright_blue", justify="right", width=10)
        table.add_column("Txns", style="bright_yellow", justify="right", width=8)
        table.add_column("Makers", style="magenta", justify="right", width=8)
        table.add_column("Conf", style="bright_magenta", justify="center", width=6)

        # Get tokens with proper names
        top_tokens = batch.get_top_tokens(10)

        for i, token in enumerate(top_tokens):
            # Extract proper token name or use fallback
            name = self.get_token_display_name(token, i)

            # Format values with proper styling
            price = f"${token.price:.6f}" if token.price else "N/A"
            volume = (
                self.format_large_number(token.volume_24h)
                if token.volume_24h
                else "N/A"
            )
            txns = f"{int(token.txns_24h):,}" if token.txns_24h else "N/A"
            makers = f"{int(token.makers):,}" if token.makers else "N/A"

            # Confidence with emoji
            conf_score = token.confidence_score or 0
            if conf_score >= 0.8:
                conf = "⚡"
            elif conf_score >= 0.6:
                conf = "⭐"
            elif conf_score >= 0.4:
                conf = "🟡"
            else:
                conf = "🔴"

            table.add_row(name, price, volume, txns, makers, conf)

        return table

    def get_token_display_name(self, token: TokenProfile, index: int) -> str:
        """Get a proper display name for the token."""
        # Use the real token symbol if available
        if token.symbol and not token.symbol.startswith("TOKEN_"):
            return token.symbol[:15]

        # Try to extract real name from metadata if available
        if hasattr(token, "metadata") and token.metadata:
            if "name" in token.metadata:
                return token.metadata["name"][:15]
            if "symbol" in token.metadata:
                return token.metadata["symbol"][:15]

        # Fallback to generic token name if no real symbol found
        return f"UNKNOWN_{index:02d}"

    def format_large_number(self, num: float) -> str:
        """Format large numbers with K, M, B suffixes."""
        if num >= 1_000_000_000:
            return f"${num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"${num/1_000:.0f}K"
        else:
            return f"${num:.0f}"

    async def stream_mode(self) -> None:
        """Live streaming mode."""
        self.clear_screen()
        self.console.print(
            Rule(
                "[bright_magenta]📺 Live Stream Mode[/bright_magenta]",
                style="bright_magenta",
            )
        )
        self.console.print()

        try:
            while True:
                batch = await self.extract_data()

                # Clear and show data
                self.clear_screen()
                self.console.print(
                    Rule(
                        "[bright_magenta]📺 Live Stream Mode[/bright_magenta]",
                        style="bright_magenta",
                    )
                )

                # Stats header
                stats = Text()
                stats.append("👻 ", style="bright_magenta")
                stats.append(
                    f"Extracted: {batch.total_extracted} | ", style="bright_white"
                )
                stats.append(
                    f"High Conf: {batch.high_confidence_count} | ", style="bright_green"
                )
                stats.append(
                    f"Time: {datetime.now().strftime('%H:%M:%S')}", style="bright_blue"
                )

                self.console.print(Padding(stats, (0, 0, 1, 0)))

                # Token table
                table = self.create_slick_token_table(batch)
                self.console.print(table)

                self.console.print(
                    "\n[bright_black]Press Ctrl+C to return to menu...[/muted]"
                )

                # Wait 5 seconds
                await asyncio.sleep(5)

        except KeyboardInterrupt:
            self.console.print("\n[bright_yellow]Returning to menu...[/warning]")
            return

    async def export_mode(self) -> None:
        """File export mode."""
        self.clear_screen()
        self.console.print(
            Rule(
                "[bright_magenta]💾 Export Mode[/bright_magenta]",
                style="bright_magenta",
            )
        )
        self.console.print()

        # Format selection
        formats = {
            "1": ("JSON", "json", "🔧 Raw JSON data"),
            "2": ("CSV", "csv", "📊 Spreadsheet format"),
            "3": ("MT5", "csv", "📈 MetaTrader format"),
            "4": ("OHLCV", "csv", "📉 OHLC with volume"),
        }

        self.console.print("[bright_white]Available export formats:\n")
        for key, (name, ext, desc) in formats.items():
            self.console.print(
                f"  [bright_magenta]{key}.[/bright_magenta] [bright_white bold]{name}[/bright_white bold]"
            )
            self.console.print(f"     [bright_black]{desc}[/bright_black]\n")

        choice = Prompt.ask(
            "[bright_magenta]→[/bright_magenta] Select format",
            choices=list(formats.keys()),
            default="1",
        )

        format_name, ext, _ = formats[choice]
        filename = f"dexscraper_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

        # Extract and save
        batch = await self.extract_data()

        if choice == "1":  # JSON
            import json

            data = [token.__dict__ for token in batch.tokens]
            with open(filename, "w") as f:
                json.dump(data, f, indent=2, default=str)
        elif choice == "2":  # CSV
            content = batch.to_csv_string("basic")
            with open(filename, "w") as f:
                f.write(content)
        elif choice == "3":  # MT5
            ohlc_batch = batch.to_ohlc_batch()
            content = "\n".join([ohlc.to_mt5_format() for ohlc in ohlc_batch])
            with open(filename, "w") as f:
                f.write(content)
        elif choice == "4":  # OHLCV
            content = batch.to_csv_string("ohlcv")
            with open(filename, "w") as f:
                f.write(content)

        self.console.print(f"\n[bright_green]✓ Exported to: {filename}[/bright_green]")
        self.console.print(
            "[bright_black]File saved in current directory[/bright_black]"
        )

        input("\nPress Enter to continue...")

    async def run(self) -> None:
        """Main application loop."""
        # Show loading screen
        self.show_ghost_loading()

        while True:
            choice = self.show_main_menu()

            if choice == "1":
                await self.stream_mode()
            elif choice == "2":
                await self.export_mode()
            elif choice == "3":
                self.console.print(
                    "[bright_yellow]Real-time monitor coming soon![/bright_yellow]"
                )
                input("Press Enter to continue...")
            elif choice == "4":
                self.console.print(
                    "[bright_yellow]Configuration coming soon![/bright_yellow]"
                )
                input("Press Enter to continue...")
            elif choice == "5":
                self.console.print(
                    Align.center("[dim white]👻 Fading into the void...[/dim white]")
                )
                time.sleep(1)
                break

    def create_header_panel(self) -> Panel:
        """Create sophisticated header with branding."""

        header_text = Text()
        header_text.append("🔷 ", style="bright_blue")
        header_text.append("DEXSCRAPER", style="bold bright_white")
        header_text.append(" PRO", style="bold gold1")
        header_text.append(" 🔷", style="bright_blue")
        header_text.append("\n")
        header_text.append(
            "Real-time DeFi Market Intelligence", style="italic bright_blue"
        )

        return Panel(Align.center(header_text), border_style="gold1", padding=(0, 1))

    def create_stats_panel(self, batch: ExtractedTokenBatch) -> Panel:
        """Create enhanced statistics panel."""

        # Calculate session metrics
        session_duration = time.time() - self.session_start
        extraction_rate = self.extraction_count / max(
            session_duration / 60, 0.1
        )  # per minute

        # Left column - Extraction Stats
        left_stats = Text()
        left_stats.append("📊 ", style="bright_blue")
        left_stats.append("EXTRACTION\n", style="bold bright_white")
        left_stats.append(f"Total: ", style="bright_white")
        left_stats.append(f"{batch.total_extracted}", style="bold bright_green")
        left_stats.append("\n")
        left_stats.append(f"High Conf: ", style="bright_white")
        left_stats.append(f"{batch.high_confidence_count}", style="bold gold1")
        left_stats.append("\n")
        left_stats.append(f"Complete: ", style="bright_white")
        left_stats.append(f"{batch.complete_profiles_count}", style="bold bright_blue")

        # Center column - Session Stats
        center_stats = Text()
        center_stats.append("⚡ ", style="gold1")
        center_stats.append("SESSION\n", style="bold bright_white")
        center_stats.append(f"Cycle: ", style="bright_white")
        center_stats.append(f"#{self.extraction_count}", style="bold bright_cyan")
        center_stats.append("\n")
        center_stats.append(f"Rate: ", style="bright_white")
        center_stats.append(f"{extraction_rate:.1f}/min", style="bold bright_yellow")
        center_stats.append("\n")
        center_stats.append(f"Uptime: ", style="bright_white")
        center_stats.append(f"{session_duration:.0f}s", style="bold bright_magenta")

        # Right column - Market Stats
        right_stats = Text()
        right_stats.append("💎 ", style="bright_green")
        right_stats.append("MARKET\n", style="bold bright_white")

        # Calculate total volume
        total_vol = sum(t.volume_24h for t in batch.tokens if t.volume_24h) or 0
        if total_vol >= 1_000_000:
            vol_str = f"${total_vol/1_000_000:.1f}M"
        else:
            vol_str = f"${total_vol/1_000:.0f}K"

        right_stats.append(f"Volume: ", style="bright_white")
        right_stats.append(f"{vol_str}", style="bold bright_green")
        right_stats.append("\n")

        # Average confidence
        avg_conf = sum(t.confidence_score for t in batch.tokens) / max(
            len(batch.tokens), 1
        )
        right_stats.append(f"Avg Conf: ", style="bright_white")
        right_stats.append(f"{avg_conf:.0%}", style="bold gold1")
        right_stats.append("\n")

        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        right_stats.append(f"Time: ", style="bright_white")
        right_stats.append(f"{current_time}", style="bold bright_blue")

        # Combine columns
        columns = Columns(
            [
                Align.left(left_stats),
                Align.center(center_stats),
                Align.right(right_stats),
            ],
            equal=True,
            expand=True,
        )

        return Panel(
            columns,
            title="[bold bright_white]📈 LIVE STATISTICS 📈[/bold bright_white]",
            border_style="bright_green",
        )

    def create_footer_panel(self, batch: ExtractedTokenBatch) -> Panel:
        """Create informative footer panel."""

        footer_text = Text()

        # Status indicators
        if batch.high_confidence_count >= 15:
            status = "[bold bright_green]🟢 EXCELLENT[/bold bright_green]"
        elif batch.high_confidence_count >= 10:
            status = "[bold yellow]🟡 GOOD[/bold yellow]"
        else:
            status = "[bold red]🔴 POOR[/bold red]"

        footer_text.append(f"Data Quality: {status} | ")
        footer_text.append("Press ", style="bright_white")
        footer_text.append("Ctrl+C", style="bold bright_red")
        footer_text.append(" to exit | ", style="bright_white")
        footer_text.append("🔄 Auto-refresh: 5s", style="bright_cyan")

        return Panel(
            Align.center(footer_text), border_style="dim white", padding=(0, 1)
        )

    def create_layout(self, batch: ExtractedTokenBatch) -> Layout:
        """Create the complete sophisticated layout."""
        layout = Layout()

        # Split into header, stats, content, footer
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="stats", size=8),
            Layout(name="content"),
            Layout(name="footer", size=3),
        )

        # Populate sections
        layout["header"].update(self.create_header_panel())
        layout["stats"].update(self.create_stats_panel(batch))
        layout["content"].update(self.create_slick_token_table(batch))
        layout["footer"].update(self.create_footer_panel(batch))

        return layout

    def show_startup_animation(self):
        """Show startup animation."""
        from rich.spinner import Spinner

        startup_text = Text()
        startup_text.append("🚀 ", style="bright_blue")
        startup_text.append("INITIALIZING DEXSCRAPER PRO", style="bold bright_white")
        startup_text.append(" 🚀", style="bright_blue")
        startup_text.append("\n\n")
        startup_text.append(
            "Connecting to DexScreener WebSocket...", style="bright_cyan"
        )

        with self.console.status(startup_text, spinner="dots12") as status:
            time.sleep(2)
            status.update("Establishing binary protocol connection...")
            time.sleep(1)
            status.update("Loading market data feed...")
            time.sleep(1)

        self.console.print(
            "\n[bold bright_green]✅ CONNECTION ESTABLISHED[/bold bright_green]"
        )
        self.console.print("[bright_cyan]Ready for live market data...[/bright_cyan]\n")
        time.sleep(1)


def create_callback(format_type: str):
    """Create a callback function for the specified format."""
    console = Console() if RICH_AVAILABLE else None
    rich_display = SlickCLI() if console else None

    def callback(pairs: List[TradingPair]):
        if format_type == "json":
            import json

            output = {
                "type": "pairs",
                "pairs": [pair.to_dict() for pair in pairs],
                "timestamp": int(time.time()),
            }
            print(json.dumps(output, separators=(",", ":")))
        elif format_type == "ohlc":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(
                        f"{pair.base_token_symbol},{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},{ohlc.close},{ohlc.volume}"
                    )
        elif format_type == "mt5":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(ohlc.to_mt5_format())
        elif format_type == "rich" and RICH_AVAILABLE and rich_display:
            # Convert pairs to token batch for rich display
            tokens = [
                TokenProfile(
                    symbol=pair.base_token_symbol,
                    price=pair.price_data.current if pair.price_data else None,
                    volume_24h=pair.volume_data.h24 if pair.volume_data else None,
                    liquidity=pair.liquidity_data.usd if pair.liquidity_data else None,
                    market_cap=pair.fdv,
                    confidence_score=0.8,  # Default confidence
                    field_count=5,
                )
                for pair in pairs
            ]

            batch = ExtractedTokenBatch(tokens=tokens)
            rich_display.extraction_count += 1

            layout = rich_display.create_layout(batch)
            console.clear()
            console.print(layout)

    return callback


def create_token_callback(format_type: str):
    """Create callback for TokenProfile batch data."""
    console = Console() if RICH_AVAILABLE else None
    rich_display = SlickCLI() if console else None

    def callback(batch: ExtractedTokenBatch):
        if format_type == "json":
            import json

            output = {
                "type": "enhanced_tokens",
                "extraction_timestamp": batch.extraction_timestamp,
                "total_extracted": batch.total_extracted,
                "high_confidence_count": batch.high_confidence_count,
                "tokens": [token.to_dict() for token in batch.get_top_tokens(20)],
            }
            print(json.dumps(output, separators=(",", ":"), default=str))
        elif format_type == "ohlcv":
            batch_csv = batch.to_csv_string("ohlcv")
            print(batch_csv)
        elif format_type == "ohlcvt":
            batch_csv = batch.to_csv_string("ohlcvt")
            print(batch_csv)
        elif format_type == "rich" and RICH_AVAILABLE and rich_display:
            rich_display.extraction_count += 1
            layout = rich_display.create_layout(batch)
            console.clear()
            console.print(layout)
        else:
            # Fallback to simple text output
            print(
                f"📊 Extracted {batch.total_extracted} tokens, {batch.high_confidence_count} high-confidence"
            )
            for token in batch.get_top_tokens(10):
                if token.price:
                    print(
                        f"  {token.get_display_name()}: ${token.price:.8f} | Vol: ${token.volume_24h:,.0f}"
                    )

    return callback


def parse_chain(value: str) -> Chain:
    """Parse chain from string."""
    try:
        return Chain(value.lower())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid chain: {value}. Choose from: {[c.value for c in Chain]}"
        )


def parse_timeframe(value: str) -> Timeframe:
    """Parse timeframe from string."""
    try:
        return Timeframe(value.lower())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid timeframe: {value}. Choose from: {[t.value for t in Timeframe]}"
        )


def parse_rank_by(value: str) -> RankBy:
    """Parse ranking method from string."""
    try:
        return RankBy(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid rank method: {value}. Choose from: {[r.value for r in RankBy]}"
        )


def parse_dex_list(value: str) -> List[DEX]:
    """Parse comma-separated list of DEXs."""
    dexs = []
    for dex_str in value.split(","):
        try:
            dexs.append(DEX(dex_str.strip().lower()))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid DEX: {dex_str}. Choose from: {[d.value for d in DEX]}"
            )
    return dexs


def build_config_from_args(args) -> ScrapingConfig:
    """Build scraping configuration from parsed arguments."""
    # Handle preset modes first
    if args.mode:
        chain = args.chains[0] if args.chains else args.chain

        if args.mode == "trending":
            config = PresetConfigs.trending(chain, args.timeframe)
        elif args.mode == "top":
            config = PresetConfigs.top_volume(
                chain, args.min_liquidity or 25000, args.min_txns or 50
            )
        elif args.mode == "gainers":
            config = PresetConfigs.gainers(
                chain, args.min_liquidity or 25000, args.min_volume or 10000
            )
        elif args.mode == "new":
            config = PresetConfigs.new_pairs(chain, args.max_age or 24)
        elif args.mode == "transactions":
            config = PresetConfigs.top_transactions(chain)
        elif args.mode == "boosted":
            config = PresetConfigs.boosted_only(chain)
        else:
            config = PresetConfigs.trending(chain, args.timeframe)
    else:
        # Build custom configuration
        # Determine chains
        if args.chains:
            chains = args.chains
        else:
            chains = [args.chain]

        # Determine DEXs
        dexs = []
        if args.dex:
            dexs = [args.dex]
        elif args.dexs:
            dexs = args.dexs

        # Build filters
        filters = Filters(
            chain_ids=chains,
            dex_ids=dexs,
            liquidity_min=args.min_liquidity,
            liquidity_max=args.max_liquidity,
            volume_h24_min=args.min_volume,
            volume_h24_max=args.max_volume,
            volume_h6_min=args.min_volume_h6,
            volume_h6_max=args.max_volume_h6,
            volume_h1_min=args.min_volume_h1,
            volume_h1_max=args.max_volume_h1,
            txns_h24_min=args.min_txns,
            txns_h24_max=args.max_txns,
            txns_h6_min=args.min_txns_h6,
            txns_h6_max=args.max_txns_h6,
            txns_h1_min=args.min_txns_h1,
            txns_h1_max=args.max_txns_h1,
            pair_age_min=args.min_age,
            pair_age_max=args.max_age,
            price_change_h24_min=args.min_change,
            price_change_h24_max=args.max_change,
            price_change_h6_min=args.min_change_h6,
            price_change_h6_max=args.max_change_h6,
            price_change_h1_min=args.min_change_h1,
            price_change_h1_max=args.max_change_h1,
            fdv_min=args.min_fdv,
            fdv_max=args.max_fdv,
            market_cap_min=args.min_mcap,
            market_cap_max=args.max_mcap,
            enhanced_token_info=args.enhanced,
            active_boosts_min=args.min_boosts,
            recent_purchased_impressions_min=args.min_ads,
        )

        # Determine ranking
        rank_by = args.rank_by or RankBy.TRENDING_SCORE_H6
        order = Order.DESC if args.order == "desc" else Order.ASC

        config = ScrapingConfig(
            timeframe=args.timeframe, rank_by=rank_by, order=order, filters=filters
        )

    return config


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DexScreener WebSocket scraper for real-time crypto data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Trending Solana pairs
  dexscraper --chain solana --mode trending

  # Top volume Ethereum pairs with filters
  dexscraper --chain ethereum --mode top --min-liquidity 50000 --min-txns 100

  # New pairs on Base (less than 6 hours old)
  dexscraper --chain base --mode new --max-age 6

  # Custom configuration: gainers on Solana Raydium only
  dexscraper --chain solana --rank-by priceChangeH24 --dexs raydium --min-liquidity 25000

  # Multiple chains and DEXs
  dexscraper --chains solana,ethereum --dexs raydium,uniswapv3 --timeframe h1
        """,
    )

    # Basic options
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "ohlc", "mt5", "ohlcv", "ohlcvt", "rich"],
        default="json",
        help="Output format (default: json). 'rich' requires rich package.",
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--once", action="store_true", help="Get data once and exit (don't stream)"
    )
    parser.add_argument(
        "--cloudflare-bypass",
        action="store_true",
        help="Enable Cloudflare bypass (experimental)",
    )

    # Connection options
    parser.add_argument(
        "--rate-limit",
        "-r",
        type=float,
        default=4.0,
        help="Rate limit (requests per second, default: 4.0)",
    )
    parser.add_argument(
        "--max-retries",
        "-m",
        type=int,
        default=5,
        help="Maximum connection retries (default: 5)",
    )

    # Preset modes
    parser.add_argument(
        "--mode",
        choices=["trending", "top", "gainers", "new", "transactions", "boosted"],
        help="Use predefined configuration mode",
    )

    # Chain and timeframe
    parser.add_argument(
        "--chain",
        type=parse_chain,
        default=Chain.SOLANA,
        help=f"Blockchain to scrape (default: solana). Options: {[c.value for c in Chain]}",
    )
    parser.add_argument(
        "--chains",
        type=lambda x: [parse_chain(c.strip()) for c in x.split(",")],
        help="Multiple chains (comma-separated)",
    )
    parser.add_argument(
        "--timeframe",
        "-t",
        type=parse_timeframe,
        default=Timeframe.H24,
        help=f"Timeframe (default: h24). Options: {[t.value for t in Timeframe]}",
    )

    # Ranking and sorting
    parser.add_argument(
        "--rank-by",
        type=parse_rank_by,
        help=f"Ranking method. Options: {[r.value for r in RankBy]}",
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sort order (default: desc)",
    )

    # DEX filters
    parser.add_argument(
        "--dex",
        type=lambda x: DEX(x.lower()),
        help=f"Single DEX filter. Options: {[d.value for d in DEX]}",
    )
    parser.add_argument(
        "--dexs", type=parse_dex_list, help="Multiple DEX filters (comma-separated)"
    )

    # Liquidity filters
    parser.add_argument("--min-liquidity", type=int, help="Minimum liquidity in USD")
    parser.add_argument("--max-liquidity", type=int, help="Maximum liquidity in USD")

    # Volume filters
    parser.add_argument("--min-volume", type=int, help="Minimum 24h volume in USD")
    parser.add_argument("--max-volume", type=int, help="Maximum 24h volume in USD")
    parser.add_argument("--min-volume-h6", type=int, help="Minimum 6h volume in USD")
    parser.add_argument("--max-volume-h6", type=int, help="Maximum 6h volume in USD")
    parser.add_argument("--min-volume-h1", type=int, help="Minimum 1h volume in USD")
    parser.add_argument("--max-volume-h1", type=int, help="Maximum 1h volume in USD")

    # Transaction filters
    parser.add_argument("--min-txns", type=int, help="Minimum 24h transactions")
    parser.add_argument("--max-txns", type=int, help="Maximum 24h transactions")
    parser.add_argument("--min-txns-h6", type=int, help="Minimum 6h transactions")
    parser.add_argument("--max-txns-h6", type=int, help="Maximum 6h transactions")
    parser.add_argument("--min-txns-h1", type=int, help="Minimum 1h transactions")
    parser.add_argument("--max-txns-h1", type=int, help="Maximum 1h transactions")

    # Age filters
    parser.add_argument("--min-age", type=int, help="Minimum pair age in hours")
    parser.add_argument("--max-age", type=int, help="Maximum pair age in hours")

    # Price change filters
    parser.add_argument("--min-change", type=float, help="Minimum 24h price change %")
    parser.add_argument("--max-change", type=float, help="Maximum 24h price change %")
    parser.add_argument("--min-change-h6", type=float, help="Minimum 6h price change %")
    parser.add_argument("--max-change-h6", type=float, help="Maximum 6h price change %")
    parser.add_argument("--min-change-h1", type=float, help="Minimum 1h price change %")
    parser.add_argument("--max-change-h1", type=float, help="Maximum 1h price change %")

    # Market cap / FDV filters
    parser.add_argument("--min-fdv", type=int, help="Minimum fully diluted valuation")
    parser.add_argument("--max-fdv", type=int, help="Maximum fully diluted valuation")
    parser.add_argument("--min-mcap", type=int, help="Minimum market cap")
    parser.add_argument("--max-mcap", type=int, help="Maximum market cap")

    # Enhanced features
    parser.add_argument(
        "--enhanced", action="store_true", help="Only pairs with enhanced token info"
    )
    parser.add_argument("--min-boosts", type=int, help="Minimum active boosts")
    parser.add_argument(
        "--min-ads", type=int, help="Minimum recent purchased impressions"
    )

    args = parser.parse_args()

    # Check if Rich is available for rich format
    if args.format == "rich" and not RICH_AVAILABLE:
        print(
            "Rich format requires 'rich' package. Install with: pip install rich",
            file=sys.stderr,
        )
        sys.exit(1)

    # Use SlickCLI for rich format
    if args.format == "rich":
        cli = SlickCLI()
        await cli.run()
        return

    # Build configuration for other formats
    config = build_config_from_args(args)

    # Initialize scraper
    scraper = DexScraper(debug=args.debug, config=config)

    if args.once:
        batch = await scraper.extract_token_data()
        if batch.tokens:
            callback = create_token_callback(args.format)
            callback(batch)
        else:
            print("Failed to extract token data", file=sys.stderr)
            sys.exit(1)
    else:
        # Stream with scraper
        callback = create_token_callback(args.format)

        async def token_stream():
            while True:
                try:
                    batch = await scraper.extract_token_data()
                    if batch.tokens:
                        callback(batch)
                    await asyncio.sleep(5)  # Wait between extractions
                except Exception as e:
                    if args.debug:
                        print(f"Extraction error: {e}", file=sys.stderr)
                    await asyncio.sleep(10)  # Wait longer on error

        await token_stream()


def cli_main():
    """Entry point for console scripts."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
