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
dexscraper trending --chain solana --limit 10
```

**Export to File**:
```bash
dexscraper trending --chain ethereum --output pairs.json --format json
dexscraper trending --chain solana --output ohlc.csv --format ohlc-csv
```

**Filter by DEX and Volume**:
```bash
dexscraper trending --dex raydium,orca --min-volume 50000 --min-liquidity 10000
```

### Programmatic Usage

```python
import asyncio
from dexscraper import DexScraper, ScrapingConfig, Chain, RankBy

# Simple trending pairs
async def get_trending():
    scraper = DexScraper(debug=True)
    pairs = await scraper.get_pairs(limit=10)
    for pair in pairs:
        print(f"{pair.base_token_symbol}: ${pair.price_data.usd:.6f}")

# Custom configuration
config = ScrapingConfig(
    chains=[Chain.SOLANA, Chain.ETHEREUM],
    rank_by=RankBy.VOLUME,
    min_liquidity_usd=50000
)

scraper = DexScraper(config=config, use_cloudflare_bypass=True)
asyncio.run(get_trending())
```

**Real-time Streaming**:
```python
async def stream_pairs():
    scraper = DexScraper()
    async for batch in scraper.stream_pairs():
        print(f"Received {len(batch.pairs)} pairs")
        for pair in batch.pairs:
            if pair.price_data.change_24h and pair.price_data.change_24h > 10:
                print(f"🚀 {pair.base_token_symbol} +{pair.price_data.change_24h:.1f}%")

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
config = PresetConfigs.high_volume(chain=Chain.ETHEREUM)

# Multi-chain DeFi focus
config = PresetConfigs.defi_focus()
```

### Custom Configuration
```python
from dexscraper import ScrapingConfig, Chain, RankBy, DEX, Filters

config = ScrapingConfig(
    chains=[Chain.SOLANA, Chain.BASE],
    rank_by=RankBy.VOLUME,
    order=Order.DESC,
    dexes=[DEX.RAYDIUM, DEX.ORCA],
    filters=Filters(
        min_liquidity_usd=10000,
        min_volume_24h_usd=50000,
        min_fdv_usd=100000,
        max_age_hours=72
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