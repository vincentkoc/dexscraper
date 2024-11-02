import asyncio
import websockets
import json
import ssl
import logging
from datetime import datetime
import urllib.parse
import struct

DEBUG = False  # Change to True for debugging

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_string(s):
    """Clean control characters and invalid UTF-8 from strings"""
    if not s:
        return ""
    return ''.join(char for char in s if ord(char) >= 32 and ord(char) < 127)

def decode_metrics(data, start_pos):
    """Decode numeric metrics from binary data"""
    try:
        metrics = {}
        doubles = struct.unpack('8d', data[start_pos:start_pos+64])

        # Map the doubles to metrics - use generic names if unsure
        field_names = [
            'price', 'priceUsd', 'priceChangeH24',
            'liquidityUsd', 'volumeH24', 'fdv',
            'timestamp', 'metric7'
        ]

        for i, value in enumerate(field_names):
            if not (value == 'timestamp' and doubles[i] < 0):  # Skip invalid timestamps
                metrics[value] = doubles[i]

        return metrics, start_pos + 64
    except:
        return {}, start_pos

def read_string(data, start_pos):
    """Read a length-prefixed string from binary data"""
    try:
        if start_pos >= len(data):
            return "", start_pos

        str_len = data[start_pos]
        start_pos += 1

        if str_len == 0 or start_pos + str_len > len(data):
            return "", start_pos

        value = data[start_pos:start_pos + str_len].decode('utf-8', errors='ignore')
        return clean_string(value), start_pos + str_len
    except:
        return "", start_pos

def decode_pair(data):
    """Decode a single trading pair from binary data"""
    try:
        pos = 0
        pair = {}

        # Read strings
        for field in ['chain', 'protocol', 'pairAddress', 'baseTokenName', 'baseTokenSymbol', 'baseTokenAddress']:
            value, pos = read_string(data, pos)
            if value:  # Only add non-empty values
                pair[field] = value

        # Read metrics
        metrics, pos = decode_metrics(data, pos)

        # Convert metrics to expected format
        if 'price' in metrics:
            pair['price'] = metrics['price']
        if 'priceUsd' in metrics:
            pair['priceUsd'] = metrics['priceUsd']
        if 'priceChangeH24' in metrics:
            pair['priceChange'] = {'h24': metrics['priceChangeH24']}
        if 'liquidityUsd' in metrics:
            pair['liquidity'] = {'usd': metrics['liquidityUsd']}
        if 'volumeH24' in metrics:
            pair['volume'] = {'h24': metrics['volumeH24']}
        if 'fdv' in metrics:
            pair['fdv'] = metrics['fdv']
        if 'timestamp' in metrics and metrics['timestamp'] > 0:
            pair['pairCreatedAt'] = int(metrics['timestamp'])
            try:
                pair['pairCreatedAtFormatted'] = datetime.fromtimestamp(metrics['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pair['pairCreatedAtFormatted'] = "1970-01-01 00:00:00"

        return pair
    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding pair: {str(e)}")
        return None

def decode_message(data):
    """Decode a complete WebSocket message"""
    try:
        if not data.startswith(b'\x00\n1.3.0\n'):
            return None

        pairs_start = data.find(b'pairs')
        if pairs_start == -1:
            return None

        pos = pairs_start + 5  # Skip "pairs"
        pairs = []

        while pos < len(data):
            # Look for valid pair data
            pair = decode_pair(data[pos:pos+512])  # Use fixed chunk size
            if pair and any(pair.values()):  # Only add pairs with actual data
                pairs.append(pair)
            pos += 512

        return {"type": "pairs", "pairs": pairs} if pairs else None

    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding message: {str(e)}")
        return None

async def connect_to_dexscreener():
    base_uri = "wss://io.dexscreener.com/dex/screener/v4/pairs/h24/1"
    params = {
        "rankBy[key]": "trendingScoreH6",
        "rankBy[order]": "desc",
        "filters[chainIds][0]": "solana"
    }
    uri = f"{base_uri}?{urllib.parse.urlencode(params)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-WebSocket-Version': '13',
        'Origin': 'https://dexscreener.com',
        'Connection': 'Upgrade',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'Upgrade': 'websocket',
    }

    ssl_context = ssl.create_default_context()

    async with websockets.connect(
        uri,
        extra_headers=headers,
        ssl=ssl_context,
        max_size=None,
    ) as websocket:
        while True:
            try:
                message = await websocket.recv()

                # Handle ping-pong
                if message == "ping":
                    await websocket.send("pong")
                    continue

                # Handle binary messages
                if isinstance(message, bytes):
                    data = decode_message(message)
                    if data and 'pairs' in data:
                        print(json.dumps(data, indent=None))

            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                if DEBUG:
                    logger.error(f"Error: {str(e)}")
                continue

async def main():
    while True:
        try:
            await connect_to_dexscreener()
        except Exception:
            await asyncio.sleep(1)
            continue

if __name__ == "__main__":
    asyncio.run(main())
