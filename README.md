# Dexscraper: 👻 DexScreener Real-time WebSocket Python Package

[![PyPI version](https://badge.fury.io/py/dexscraper.svg)](https://badge.fury.io/py/dexscraper)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CI](https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml/badge.svg)](https://github.com/vincentkoc/dexscraper/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/vincentkoc/dexscraper/branch/main/graph/badge.svg)](https://codecov.io/gh/vincentkoc/dexscraper)

> ⚠️ **RESEARCH & EDUCATIONAL PURPOSE ONLY** ⚠️
> This project is completely **INDEPENDENT** and has **NO AFFILIATION** with DexScreener.
> Use at your own risk for trading and ensure compliance with DexScreener's terms of service.

A comprehensive Python package for real-time cryptocurrency trading data from DexScreener's WebSocket API. Supports multiple blockchain networks with rich CLI interface and programmatic access.

## ✨ Features

### 🏗️ **Professional Package Architecture**
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

### 📊 **Data Processing**
- **Real-time WebSocket**: Direct connection to DexScreener's binary protocol
- **OHLC Data**: MetaTrader-compatible candlestick data
- **Token Profiles**: Enhanced metadata with social links and descriptions
- **Market Metrics**: Price, volume, liquidity, FDV, market cap
- **Advanced Filtering**: By trending score, volume, price changes, liquidity

### 🛡️ **Enterprise-Ready**
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

### Requirements
- **Python 3.9+**
- **Core**: `websockets>=10.0`, `cloudscraper>=1.2.60`
- **CLI**: `rich` (optional, for enhanced terminal interface)
- **Dev**: `pytest`, `black`, `mypy`, `pre-commit`

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

### JSON Format (Default)
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

### OHLC Format (MetaTrader Compatible)
```csv
Timestamp,Symbol,Open,High,Low,Close,Volume
1642248600,EXAM/USDC,1.20,1.35,1.18,1.25,75000
```

### Token Profile Format
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

## 🏗️ Architecture Overview

### Core Components

#### `DexScraper` (Main Class)
- **WebSocket Management**: Secure connections with automatic reconnection
- **Protocol Decoder**: Binary message parsing and validation
- **Rate Limiting**: Configurable request throttling
- **Error Recovery**: Exponential backoff with max retry limits

#### `ScrapingConfig` (Configuration)
- **Multi-Chain**: Support for 8+ blockchain networks
- **Flexible Filtering**: By DEX, volume, liquidity, market cap
- **Ranking Options**: Trending score, volume, price changes
- **Preset Configs**: Ready-to-use configurations for common scenarios

#### `Models` (Data Structures)
- **TradingPair**: Complete pair information with typed fields
- **TokenProfile**: Enhanced metadata with social links
- **OHLCData**: MetaTrader-compatible candlestick data
- **ExtractedTokenBatch**: Batch processing with metadata

#### `CLI` (Command Interface)
- **Rich Integration**: Beautiful tables and live updates
- **Interactive Mode**: Real-time pair monitoring
- **Export Options**: Multiple output formats
- **Filtering UI**: Dynamic configuration through prompts

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

## 🛡️ Security & Reliability

### Security Features
- **SSL/TLS**: All connections use secure WebSocket (WSS)
- **Input Sanitization**: Comprehensive string cleaning and validation
- **Dependency Scanning**: Automated security checks with Bandit and Safety
- **No Secrets**: No API keys or authentication required
- **Sandboxed**: Read-only access to public market data

### Error Handling & Recovery
- **Connection Recovery**: Automatic reconnection with exponential backoff
- **Data Validation**: Multiple layers of input validation
- **Graceful Degradation**: Continue processing on partial failures
- **Rate Limiting**: Prevent overwhelming the upstream service
- **Memory Management**: Efficient handling of large data streams

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for complete development setup, testing, and contribution workflow.

## 📄 License

**GPL-3.0** - See [LICENSE](LICENSE) for details.

## ⚖️ Important Disclaimers

### 🔬 Research & Educational Use Only

**THIS SOFTWARE IS PROVIDED FOR RESEARCH AND EDUCATIONAL PURPOSES ONLY**

- ❌ **NOT for trading or investment decisions**
- ❌ **NOT financial advice or recommendations**
- ❌ **NOT for commercial use without proper compliance**
- ✅ **FOR learning about market data structures**
- ✅ **FOR academic research and analysis**
- ✅ **FOR understanding WebSocket protocols**

### 🚫 No Affiliation with DexScreener

**THIS PROJECT IS COMPLETELY INDEPENDENT AND UNOFFICIAL**

- 🔹 **NO official relationship** with DexScreener.com
- 🔹 **NO endorsement** from DexScreener
- 🔹 **NO warranty** or guarantee of service continuity
- 🔹 **NO responsibility** for any changes to DexScreener's API
- 🔹 Users must **comply with DexScreener's Terms of Service**

### ⚠️ Risk Warnings

- **Market Risk**: Cryptocurrency markets are highly volatile and risky
- **Technical Risk**: This software may contain bugs or inaccuracies
- **Compliance Risk**: Users are responsible for regulatory compliance
- **Service Risk**: DexScreener may change or discontinue their API
- **No Guarantees**: No warranty on data accuracy, availability, or performance

### 📋 Responsible Use Guidelines

- ✅ **DO** use for learning and research
- ✅ **DO** respect DexScreener's rate limits and ToS
- ✅ **DO** verify data independently before any decisions
- ✅ **DO** understand the risks of cryptocurrency markets
- ❌ **DON'T** use for automated trading without proper risk management
- ❌ **DON'T** rely solely on this data for financial decisions
- ❌ **DON'T** abuse the service or violate terms of use

## 💝 Support Development

If this project helps your research or learning:

- ⭐ **Star this repository**
- 🐛 **Report issues and bugs**
- 🤝 **Contribute code or documentation**
- ☕ **[Buy me a coffee](https://buymeacoffee.com/vincentkoc)**
- 💖 **[Sponsor on GitHub](https://github.com/sponsors/vincentkoc)**

---

<div align="center">
  <h3>🔬 FOR RESEARCH & EDUCATIONAL USE ONLY 🔬</h3>
  <p><strong>No affiliation with DexScreener • Use at your own risk</strong></p>
  <p><sub>Built with ❤️ for the DeFi research community</sub></p>
</div>
