#!/usr/bin/env python3
"""
Backward compatibility script that maintains the original dex.py interface.
This allows existing users to run `python dex.py` as before while using the new DexScraper.
"""

import asyncio
import sys

from dexscraper import DexScraper


async def main() -> None:
    """Run with the original interface for backward compatibility."""
    print("🚀 DexScraper - Backward Compatibility Mode")
    print("📡 Starting real-time token extraction...")

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
                            token.to_dict() for token in batch.get_top_tokens(10)
                        ],
                        "timestamp": int(time.time()),
                    }
                    print(json.dumps(output, separators=(",", ":"), default=str))

                # Wait between extractions (similar to original streaming)
                await asyncio.sleep(5)

            except Exception as e:
                print(f"Extraction error: {e}", file=sys.stderr)
                await asyncio.sleep(10)

    await stream_tokens()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
