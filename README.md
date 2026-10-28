<h1 align="center">👻 Dexscraper</h1>

<p align="center">
  <strong>Real-time DexScreener market data in one CLI/SDK.</strong>
</p>

<p align="center">
  <a href="https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml"><img src="https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/dexscraper"><img src="https://badge.fury.io/py/dexscraper.svg" alt="PyPI"></a>
  <a href="https://github.com/vincentkoc/dexscraper/releases"><img src="https://img.shields.io/github/v/release/vincentkoc/dexscraper?include_prereleases" alt="Release"></a>
  <a href="https://github.com/vincentkoc/dexscraper/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vincentkoc/dexscraper" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python">
</p>

> [!IMPORTANT]
> This project is independent and not affiliated with DexScreener.<br>
> Use at your own risk for research purposes only and comply with DexScreener terms.

> [!WARNING]
> The unofficial DexScreener screener WebSocket endpoints under
> `wss://io.dexscreener.com/dex/screener/...` now return **404** and are
> treated as dead. Prefer the [official DexScreener API](https://docs.dexscreener.com/api/reference)
> (`https://api.dexscreener.com/...`) for supported market data access.
> Streaming via this package's historical `io.dexscreener.com` WebSocket
> path is not currently available.

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

<details>
<summary>Optional: Cloudflare bypass enhancements (cloudscraper v3)</summary>

```bash
# Recommended when using --cloudflare-bypass in interactive or --once modes
pip install "cloudscraper @ git+https://github.com/VeNoMouS/cloudscraper.git@3.0.0"
```

- `dexscraper` auto-detects cloudscraper major version at runtime.
- If `<3` is detected, bypass still works in compatibility mode and the CLI prints
  a one-time warning in non-streaming flows with the install command above.

</details>

## Why Dexscraper?

DexScreener data is useful, but scraping it consistently is painful: protocol changes, Cloudflare behavior, reconnect logic, and export formatting. **Dexscraper gives you one stable interface** for real-time extraction, filtering, and export, both from CLI and Python code.

## What You Get

- Real-time streaming of webSocket extraction
- Multi-chain and multi-DEX filtering
- Trending/top/gainers/new presets
- Structured token profiles and OHLC/OHLCVT output for tools like Metatrader
- Optional Cloudflare bypass flow (with runtime v3 feature detection)
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

### Options

Run `dexscraper --help` for the full list. Grouped summary:

| Area | Flags |
| --- | --- |
| Output | `--format/-f {json,ohlc,mt5,ohlcv,ohlcvt,rich}`, `--once`, `--limit N` (default 20), `--output FILE` (with `--once`), `--debug/-d` |
| Connection | `--cloudflare-bypass`, `--rate-limit/-r N` (req/s, default 4.0), `--max-retries/-m N` (default 5) |
| Presets | `--mode {trending,top,gainers,new,transactions,boosted}` |
| Scope | `--chain NAME` (default solana) or `--chains a,b`, `--dex NAME` or `--dexs a,b`, `--timeframe/-t {m5,h1,h6,h24}` (default h24) |
| Ranking | `--rank-by {trendingScoreM5,trendingScoreH1,trendingScoreH6,trendingScoreH24,volume,txns,priceChangeH24,priceChangeH6,priceChangeH1,liquidity,fdv,marketCap}`, `--order {asc,desc}` |
| Liquidity / value | `--min-liquidity`, `--max-liquidity` (USD), `--min-fdv`, `--max-fdv`, `--min-mcap`, `--max-mcap` |
| Volume (USD) | `--min-volume`, `--max-volume` (24h), `--min-volume-h6`, `--max-volume-h6`, `--min-volume-h1`, `--max-volume-h1` |
| Transactions | `--min-txns`, `--max-txns` (24h), `--min-txns-h6`, `--max-txns-h6`, `--min-txns-h1`, `--max-txns-h1` |
| Price change (%) | `--min-change`, `--max-change` (24h), `--min-change-h6`, `--max-change-h6`, `--min-change-h1`, `--max-change-h1` |
| Pair age (hours) | `--min-age`, `--max-age` |
| Promotion | `--enhanced` (enhanced token info only), `--min-boosts N`, `--min-ads N` |

Chains: solana, ethereum, base, bsc, polygon, arbitrum, optimism, avalanche.
DEXs: raydium, pumpfun, pumpswap, orca, jupiter, meteora, uniswap, uniswapv3, sushiswap, pancakeswap, aerodrome, baseswap.

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
