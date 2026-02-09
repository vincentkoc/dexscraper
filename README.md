# Dexscraper: 👻 DexScreener Real-time WebSocket Python Package

[![PyPI version](https://badge.fury.io/py/dexscraper.svg)](https://badge.fury.io/py/dexscraper)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CI](https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml/badge.svg)](https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/vincentkoc/dexscraper/branch/main/graph/badge.svg)](https://codecov.io/gh/vincentkoc/dexscraper)

> [!IMPORTANT]
> This project is completely **INDEPENDENT** and has **NO AFFILIATION** with DexScreener.
> Use at your own risk for trading and ensure compliance with DexScreener's terms of service.

Dexscraper is a comprehensive Python package and SDK for real-time cryptocurrency trading data from DexScreener's WebSocket API. Supports multiple blockchain networks with rich CLI interface and programmatic access.

## ✨ Features

### 🏗️ **Package Architecture**
- **Modular Design**: Structured as a proper Python package with clean separation of concerns
- **Type Safety**: Full type annotations with mypy support
- **Rich CLI**: Interactive command-line interface with live data visualization
- **Extensible Config**: Support for multiple chains, DEXs, and filtering options
- **Export Formats**: JSON, CSV, MetaTrader-compatible formats

### 🔗 **Multi-Chain Support**
- **Solana** (Raydium, Orca, Jupiter)
- **Ethereum** (Uniswap V2/V3, SushiSwap)
- **Base, BSC, Polygon, Arbitrum, Optimism**
- **Avalanche** and more

### 📊 **Data Processing Support**
- **Real-time WebSocket**: Direct connection to DexScreener's binary protocol
- **OHLC Data**: MetaTrader-compatible candlestick data
- **Token Profiles**: Enhanced metadata with social links and descriptions
- **Market Metrics**: Price, volume, liquidity, FDV, market cap
- **Advanced Filtering**: By trending score, volume, price changes, liquidity

### 🛡️ **Automation Ready**
- **Cloudflare Bypass**: Optional cloudscraper integration for difficult networks
- **Rate Limiting**: Configurable request throttling
- **Error Recovery**: Robust reconnection with exponential backoff
- **Data Validation**: Comprehensive input sanitization and NaN handling
- **Security**: Bandit security scanning, dependency safety checks

## 🚀 Installation

### From PyPI (Recommended)
```bash
pip install dexscraper
```

### Development Installation
```bash
git clone https://github.com/vincentkoc/dexscraper.git
cd dexscraper
pip install -e .[dev]
```

## 📖 Quick Start

### Command Line Interface

**Interactive Mode** (Rich UI):
```bash
dexscraper interactive
```

**Simple Trending Pairs**:
```bash
dexscraper trending --chain solana --limit 10 --once
```

**Export to File**:
```bash
dexscraper trending --chain ethereum --output pairs.json --format json --once
dexscraper trending --chain solana --output ohlc.csv --format ohlcvt --once
```

**Filter by DEX and Volume**:
```bash
dexscraper trending --dexs raydium,orca --min-volume 50000 --min-liquidity 10000 --once
```

### Programmatic Usage

```python
import asyncio
from dexscraper import DexScraper, ScrapingConfig, Chain, RankBy, Filters, Timeframe

# Custom configuration
config = ScrapingConfig(
    timeframe=Timeframe.H1,
    rank_by=RankBy.VOLUME,
    filters=Filters(chain_ids=[Chain.SOLANA], liquidity_min=50000),
)

scraper = DexScraper(config=config, use_cloudflare_bypass=True)

async def get_trending():
    batch = await scraper.extract_token_data()
    for token in batch.get_top_tokens(10):
        if token.price is not None:
            print(f"{token.get_display_name()}: ${token.price:.6f}")

asyncio.run(get_trending())
```

**Real-time Streaming**:
```python
async def stream_pairs():
    scraper = DexScraper()
    def on_batch(batch):
        print(f"Received {batch.total_extracted} tokens")
        for token in batch.get_top_tokens(10):
            if token.change_24h and token.change_24h > 10:
                print(f"🚀 {token.get_display_name()} +{token.change_24h:.1f}%")

    await scraper.stream_pairs(callback=on_batch, use_enhanced_extraction=True)

asyncio.run(stream_pairs())
```

## 📊 Data Formats & Export Options

<details>
<summary>JSON Format (Default)</summary>

```json
{
  "type": "pairs",
  "pairs": [
    {
      "chain": "solana",
      "dex": "raydium",
      "pairAddress": "ABC123...",
      "baseToken": {
        "name": "Example Token",
        "symbol": "EXAM",
        "address": "DEF456..."
      },
      "price": {
        "current": "1.234567",
        "usd": "1.234567",
        "change24h": "12.5"
      },
      "liquidity": {"usd": "150000.00"},
      "volume": {"h24": "75000.00"},
      "fdv": "5000000.00",
      "createdAt": "2024-01-15T10:30:00Z"
    }
  ]
}
```
</details>

<details>
<summary>OHLC Format (MetaTrader Compatible)</summary>

```csv
Timestamp,Symbol,Open,High,Low,Close,Volume
1642248600,EXAM/USDC,1.20,1.35,1.18,1.25,75000
```
</details>


<details>
<summary>Token Profile Format</summary>

```json
{
  "symbol": "EXAM",
  "name": "Example Token",
  "description": "Revolutionary DeFi token...",
  "websites": ["https://example.com"],
  "socials": {
    "twitter": "@exampletoken",
    "telegram": "t.me/example"
  }
}
```
</details>

## ⚙️ Advanced Configuration

### Preset Configurations
```python
from dexscraper import PresetConfigs

# Trending Solana pairs (default)
config = PresetConfigs.trending()

# High-volume Ethereum pairs
config = PresetConfigs.top_volume(chain=Chain.ETHEREUM)
```

### Custom Configuration
```python
from dexscraper import ScrapingConfig, Chain, RankBy, DEX, Filters

config = ScrapingConfig(
    timeframe=Timeframe.H1,
    rank_by=RankBy.VOLUME,
    order=Order.DESC,
    filters=Filters(
        chain_ids=[Chain.SOLANA, Chain.BASE],
        dex_ids=[DEX.RAYDIUM, DEX.ORCA],
        liquidity_min=10000,
        volume_h24_min=50000,
        fdv_min=100000,
        pair_age_max=72,
    )
)
```

### Rate Limiting & Reliability
```python
scraper = DexScraper(
    rate_limit=2.0,           # Max 2 requests/second
    max_retries=10,           # Retry up to 10 times
    backoff_base=2.0,         # Exponential backoff
    use_cloudflare_bypass=True # Use cloudscraper for difficult networks
)
```

## 🤝 Contributing


## 💝 Support Development

If this project helps your research or learning:

- ⭐ **Star this repository**
- 🤝 **Contribute code or documentation** We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for complete development setup, testing, and contribution workflow.
- ☕ **[Buy me a coffee](https://buymeacoffee.com/vincentkoc)**
- 💖 **[Sponsor on GitHub](https://github.com/sponsors/vincentkoc)**

---

Built with ❤️ for the DeFi research community
