"""Command line interface for dexscraper."""

import asyncio
import argparse
import sys
from typing import List

from .scraper import DexScraper
from .models import TradingPair
from .config import (ScrapingConfig, PresetConfigs, Chain, Timeframe, RankBy, Order, 
                    DEX, Filters)


def create_callback(format_type: str):
    """Create a callback function for the specified format."""
    def callback(pairs: List[TradingPair]):
        if format_type == "json":
            import json
            import time
            output = {
                "type": "pairs",
                "pairs": [pair.to_dict() for pair in pairs],
                "timestamp": int(time.time())
            }
            print(json.dumps(output, separators=(',', ':')))
        elif format_type == "ohlc":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(f"{pair.base_token_symbol},{ohlc.timestamp},{ohlc.open},{ohlc.high},{ohlc.low},{ohlc.close},{ohlc.volume}")
        elif format_type == "mt5":
            for pair in pairs:
                ohlc = pair.to_ohlc()
                if ohlc:
                    print(ohlc.to_mt5_format())
    return callback


def parse_chain(value: str) -> Chain:
    """Parse chain from string."""
    try:
        return Chain(value.lower())
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid chain: {value}. Choose from: {[c.value for c in Chain]}")


def parse_timeframe(value: str) -> Timeframe:
    """Parse timeframe from string."""
    try:
        return Timeframe(value.lower())
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid timeframe: {value}. Choose from: {[t.value for t in Timeframe]}")


def parse_rank_by(value: str) -> RankBy:
    """Parse ranking method from string."""
    try:
        return RankBy(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid rank method: {value}. Choose from: {[r.value for r in RankBy]}")


def parse_dex_list(value: str) -> List[DEX]:
    """Parse comma-separated list of DEXs."""
    dexs = []
    for dex_str in value.split(','):
        try:
            dexs.append(DEX(dex_str.strip().lower()))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid DEX: {dex_str}. Choose from: {[d.value for d in DEX]}")
    return dexs


def build_config_from_args(args) -> ScrapingConfig:
    """Build scraping configuration from parsed arguments."""
    # Handle preset modes first
    if args.mode:
        chain = args.chains[0] if args.chains else args.chain
        
        if args.mode == "trending":
            config = PresetConfigs.trending(chain, args.timeframe)
        elif args.mode == "top":
            config = PresetConfigs.top_volume(chain, args.min_liquidity or 25000, args.min_txns or 50)
        elif args.mode == "gainers":
            config = PresetConfigs.gainers(chain, args.min_liquidity or 25000, args.min_volume or 10000)
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
            timeframe=args.timeframe,
            rank_by=rank_by,
            order=order,
            filters=filters
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
        """)
    
    # Basic options
    parser.add_argument(
        "--format", "-f",
        choices=["json", "ohlc", "mt5"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Get data once and exit (don't stream)"
    )
    parser.add_argument(
        "--cloudflare-bypass",
        action="store_true",
        help="Enable Cloudflare bypass (experimental)"
    )
    
    # Connection options
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=4.0,
        help="Rate limit (requests per second, default: 4.0)"
    )
    parser.add_argument(
        "--max-retries", "-m",
        type=int,
        default=5,
        help="Maximum connection retries (default: 5)"
    )
    
    # Preset modes
    parser.add_argument(
        "--mode",
        choices=["trending", "top", "gainers", "new", "transactions", "boosted"],
        help="Use predefined configuration mode"
    )
    
    # Chain and timeframe
    parser.add_argument(
        "--chain",
        type=parse_chain,
        default=Chain.SOLANA,
        help=f"Blockchain to scrape (default: solana). Options: {[c.value for c in Chain]}"
    )
    parser.add_argument(
        "--chains",
        type=lambda x: [parse_chain(c.strip()) for c in x.split(',')],
        help="Multiple chains (comma-separated)"
    )
    parser.add_argument(
        "--timeframe", "-t",
        type=parse_timeframe,
        default=Timeframe.H24,
        help=f"Timeframe (default: h24). Options: {[t.value for t in Timeframe]}"
    )
    
    # Ranking and sorting
    parser.add_argument(
        "--rank-by",
        type=parse_rank_by,
        help=f"Ranking method. Options: {[r.value for r in RankBy]}"
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sort order (default: desc)"
    )
    
    # DEX filters
    parser.add_argument(
        "--dex",
        type=lambda x: DEX(x.lower()),
        help=f"Single DEX filter. Options: {[d.value for d in DEX]}"
    )
    parser.add_argument(
        "--dexs",
        type=parse_dex_list,
        help="Multiple DEX filters (comma-separated)"
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
    parser.add_argument("--enhanced", action="store_true", help="Only pairs with enhanced token info")
    parser.add_argument("--min-boosts", type=int, help="Minimum active boosts")
    parser.add_argument("--min-ads", type=int, help="Minimum recent purchased impressions")
    
    args = parser.parse_args()
    
    # Build configuration
    config = build_config_from_args(args)
    
    scraper = DexScraper(
        debug=args.debug,
        rate_limit=args.rate_limit,
        max_retries=args.max_retries,
        use_cloudflare_bypass=args.cloudflare_bypass,
        config=config
    )
    
    if args.once:
        pairs = await scraper.get_pairs_once()
        if pairs:
            callback = create_callback(args.format)
            callback(pairs)
        else:
            print("Failed to get data", file=sys.stderr)
            sys.exit(1)
    else:
        await scraper.run(output_format=args.format)


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