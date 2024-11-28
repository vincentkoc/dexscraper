# Dexscraper: 👻 DexScreener Public WebSocket Client Scraper

A robust Python client for connecting to DexScreener's WebSocket API to monitor real-time cryptocurrency trading pair data. This client specifically focuses on tracking trending pairs on the Solana blockchain.

## Features

- Real-time WebSocket connection to DexScreener's Public API (used to power frontend)
- Binary protocol decoding for efficient data handling
- Robust error handling and automatic reconnection
- Metric processing for trading pairs including:
  - Price data (current price and USD equivalent)
  - 24-hour price changes
  - Liquidity metrics
  - Trading volume
  - Fully Diluted Valuation (FDV)
  - Creation timestamps
- String sanitization and data validation
- Clean handling of NaN/Infinity values

## Requirements

- Python 3.7+
- websockets
- ssl
- logging
- datetime
- urllib
- struct
- decimal

## Installation

1. Clone the repository:
```bash
git clone https://github.com/vincentkoc/dexscraper.git
cd dexscraper
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the client with:

```bash
python main.py
```

The client will:
1. Establish a WebSocket connection to DexScreener
2. Monitor trending pairs on Solana
3. Process and output trading pair data in JSON format
4. Automatically handle reconnections if the connection is lost

### Debug Mode

Set `DEBUG = True` at the top of the script to enable detailed logging.

## Data Format

The client outputs JSON-formatted data with the following structure:

```json
{
    "type": "pairs",
    "pairs": [
        {
            "chain": "solana",
            "protocol": "protocol_name",
            "pairAddress": "address",
            "baseTokenName": "token_name",
            "baseTokenSymbol": "symbol",
            "baseTokenAddress": "token_address",
            "price": "current_price",
            "priceUsd": "usd_price",
            "priceChange": {
                "h24": "24hr_change"
            },
            "liquidity": {
                "usd": "usd_liquidity"
            },
            "volume": {
                "h24": "24hr_volume"
            },
            "fdv": "fully_diluted_valuation",
            "pairCreatedAt": "unix_timestamp",
            "pairCreatedAtFormatted": "YYYY-MM-DD HH:MM:SS"
        }
    ]
}
```

## Key Components

### WebSocket Connection
- Establishes secure WebSocket connection with appropriate headers
- Implements ping-pong heartbeat mechanism
- Handles connection drops with automatic reconnection

### Data Decoding
- `decode_pair()`: Processes binary data for individual trading pairs
- `decode_metrics()`: Handles numeric metrics from binary data
- `handle_double()`: Validates floating-point values
- `clean_string()`: Sanitizes string data

### Error Handling
- Comprehensive try-catch blocks
- Graceful handling of malformed data
- Automatic reconnection on connection failures
- Optional debug logging

## Configuration

The client is configured to track pairs ranked by 6-hour trending score (`trendingScoreH6`) in descending order. To modify the tracking parameters, adjust the `params` dictionary in the `connect_to_dexscreener()` function.

## Security Considerations

- Uses SSL context for secure connections
- Implements input sanitization
- Validates numeric values
- Handles potentially malicious string data

## Error Handling

The client implements multiple layers of error handling:
- Connection-level error handling with automatic reconnection
- Message-level error handling to ignore malformed messages
- Data-level validation and sanitization
- Graceful handling of invalid numeric values

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

GPL-v3

## Disclaimer

This is an unofficial client for DexScreener's WebSocket API. Use at your own risk and ensure compliance with DexScreener's terms of service.
This is not affiliated with DexScreener in any-way.
