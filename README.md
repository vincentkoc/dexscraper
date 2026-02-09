<h1 align="center">👻 Dexscraper</h1>

<p align="center">
  <strong>Real-time DexScreener market data in one CLI/SDK.</strong>
</p>

<p align="center">
  <a href="https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml"><img src="https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/dexscraper"><img src="https://badge.fury.io/py/dexscraper.svg" alt="PyPI"></a>
  <a href="https://github.com/vincentkoc/dexscraper/releases"><img src="https://img.shields.io/github/v/release/vincentkoc/dexscraper?include_prereleases" alt="Release"></a>
  <a href="https://github.com/vincentkoc/dexscraper/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vincentkoc/dexscraper" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
</p>

> [!IMPORTANT]
> This project is independent and not affiliated with DexScreener.<br>
> Use at your own risk for research purposes only and comply with DexScreener terms.

## Install Dexscraper

<details open>

<summary>Install with `pip` or `uv`</summary>

```bash
# pip install
pip install dexscraper

# or uv install
uv pip install dexscraper
```

</details>

<details>
<summary>Alternative: Development install</summary>

```bash
# download and install from main branch
git clone https://github.com/vincentkoc/dexscraper.git
cd dexscraper
pip install -e .[dev]
```

</details>

## Why Dexscraper?

DexScreener data is useful, but scraping it consistently is painful: protocol changes, Cloudflare behavior, reconnect logic, and export formatting. **Dexscraper gives you one stable interface** for real-time extraction, filtering, and export, both from CLI and Python code.

## What You Get

- Real-time streaming of webSocket extraction
- Multi-chain and multi-DEX filtering
- Trending/top/gainers/new presets
- Structured token profiles and OHLC/OHLCVT output for tools like Metatrader
- Optional Cloudflare bypass flow
- Typed Python SDK + CLI

## Commands

```bash
dexscraper                                                                    # streaming json
dexscraper interactive                                                        # gui mode
dexscraper trending --chain solana --limit 10 --once                          # trending
dexscraper top --chain ethereum --min-liquidity 50000 --once                  # top
dexscraper trending --chain solana --format json --output pairs.json --once   # trending to file
dexscraper --mode trending --chain solana --format rich                       # gui mode
```

## Python SDK

```python
import asyncio
from dexscraper import DexScraper, ScrapingConfig, Filters, Chain, RankBy, Timeframe

config = ScrapingConfig(
    timeframe=Timeframe.H1,
    rank_by=RankBy.VOLUME,
    filters=Filters(chain_ids=[Chain.SOLANA], liquidity_min=50_000),
)

async def main():
    scraper = DexScraper(config=config, use_cloudflare_bypass=True)
    batch = await scraper.extract_token_data()
    for token in batch.get_top_tokens(10):
        if token.price is not None:
            print(token.get_display_name(), token.price)

asyncio.run(main())
```

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Open an issue for bugs, start a discussion for questions, and star the repo if it helps.

---

Made with 💙 by <a href="https://github.com/vincentkoc">Vincent Koc</a> · <a href="LICENSE">GPL-3.0</a>
