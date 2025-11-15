#!/usr/bin/env python3
"""
Backward compatibility script that maintains the original dex.py interface.
This allows existing users to run `python dex.py` as before while using the new DexScraper.
"""

import argparse

import asyncio
import sys

from dexscraper import DexScraper


def positive_float(value: str) -> float:
    """argparse helper that ensures refresh interval is > 0."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("refresh interval must be greater than 0")
    return parsed


def positive_int(value: str) -> int:
    """argparse helper that ensures token limit is > 0."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("token limit must be greater than 0")
    return parsed


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for backward compatibility shim."""
    parser = argparse.ArgumentParser(
        description="Legacy DexScraper entrypoint with streaming JSON output."
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=5.0,
        help="Seconds to wait between extraction cycles (default: 5)",
    )
    parser.add_argument(
        "--top",
        type=positive_int,
        default=10,
        help="How many tokens to include in each JSON payload (default: 10)",
    )
    return parser.parse_args()


async def main(args: argparse.Namespace) -> None:
    """Run with the original interface for backward compatibility."""
    print("🚀 DexScraper - Backward Compatibility Mode")
    print(
        f"📡 Starting real-time token extraction (interval={args.interval}s, top={args.top})..."
    )

    scraper = DexScraper(debug=True)  # Enable debug by default like original

    # Stream tokens using the new extraction method
    async def stream_tokens() -> None:
        while True:
            try:
                batch = await scraper.extract_token_data()
                if batch.tokens:
                    # Output in original JSON format
                    import json
                    import time

                    output = {
                        "type": "tokens",
                        "extracted": batch.total_extracted,
                        "high_confidence": batch.high_confidence_count,
                        "tokens": [
                            token.to_dict() for token in batch.get_top_tokens(args.top)
                        ],
                        "timestamp": int(time.time()),
                    }
                    print(json.dumps(output, separators=(",", ":"), default=str))

                # Wait between extractions (similar to original streaming)
                await asyncio.sleep(args.interval)

            except Exception as e:
                print(f"Extraction error: {e}", file=sys.stderr)
                await asyncio.sleep(min(args.interval * 2, 60))

    await stream_tokens()


if __name__ == "__main__":
    cli_args = parse_args()
    try:
        asyncio.run(main(cli_args))
    except KeyboardInterrupt:
        print("\nStopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
