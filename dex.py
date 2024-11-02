import asyncio
import websockets
import json
import ssl
import logging
from datetime import datetime
import urllib.parse
import struct
from decimal import Decimal, InvalidOperation, ROUND_DOWN

DEBUG = False

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_string(s):
    """Clean invalid and control characters from strings"""
    try:
        if not s:
            return ""
        # Remove non-printable characters except spaces
        return ''.join(char for char in s if (32 <= ord(char) < 127) or ord(char) == 9)
    except:
        return ""

def is_valid_float(value):
    """Check if a float value is within reasonable bounds"""
    try:
        if not isinstance(value, (int, float)):
            return False
        # Filter out unreasonable values
        return -1e15 < value < 1e15 and str(value) != 'nan' and str(value) != 'inf' and str(value) != '-inf'
    except:
        return False

def format_float(value, decimals=8):
    """Format float with appropriate precision"""
    try:
        if not is_valid_float(value):
            return "0"

        # Use fewer decimals for larger numbers
        if abs(value) >= 1:
            decimals = min(decimals, max(2, int(8 - len(str(int(abs(value)))))))

        return f"{value:.{decimals}f}".rstrip('0').rstrip('.')
    except:
        return "0"

def decode_metrics(data, start_pos):
    """Decode numeric values from binary data"""
    try:
        if start_pos + 64 > len(data):
            return {}, start_pos

        metrics = {}
        values = struct.unpack('8d', data[start_pos:start_pos+64])

        # Map metrics to their keys with validation
        metrics_map = {
            'price': values[0],
            'priceUsd': values[1],
            'priceChangeH24': values[2],
            'liquidityUsd': values[3],
            'volumeH24': values[4],
            'fdv': values[5],
            'timestamp': values[6]
        }

        # Only include valid values
        return {k: v for k, v in metrics_map.items() if is_valid_float(v)}, start_pos + 64
    except:
        return {}, start_pos

def decode_pair(data):
    """Decode a single trading pair from binary data"""
    try:
        pos = 0
        pair = {}

        # Read strings
        for field in ['chain', 'protocol', 'pairAddress', 'baseTokenName', 'baseTokenSymbol', 'baseTokenAddress']:
            if pos >= len(data):
                break
            str_len = data[pos]
            pos += 1
            if str_len == 0 or pos + str_len > len(data):
                continue
            value = clean_string(data[pos:pos+str_len].decode('utf-8', errors='ignore'))
            if value:  # Only include non-empty values
                pair[field] = value
            pos += str_len

        # Read metrics
        metrics, pos = decode_metrics(data, pos)

        if metrics:
            pair['price'] = format_float(metrics.get('price', 0))
            pair['priceUsd'] = format_float(metrics.get('priceUsd', 0))
            pair['priceChange'] = {'h24': format_float(metrics.get('priceChangeH24', 0))}
            pair['liquidity'] = {'usd': format_float(metrics.get('liquidityUsd', 0))}
            pair['volume'] = {'h24': format_float(metrics.get('volumeH24', 0))}
            pair['fdv'] = format_float(metrics.get('fdv', 0))

            if 'timestamp' in metrics and 0 <= metrics['timestamp'] < 4102444800:  # Valid timestamp range
                pair['pairCreatedAt'] = int(metrics['timestamp'])
                try:
                    pair['pairCreatedAtFormatted'] = datetime.fromtimestamp(pair['pairCreatedAt']).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pair['pairCreatedAtFormatted'] = "1970-01-01 00:00:00"
            else:
                pair['pairCreatedAt'] = 0
                pair['pairCreatedAtFormatted'] = "1970-01-01 00:00:00"

        # Only return pairs with valid data
        if len(pair) > 2 and any(v != "0" for v in [pair.get('price'), pair.get('priceUsd'),
            pair.get('volume', {}).get('h24', "0"), pair.get('liquidity', {}).get('usd', "0")]):
            return pair

        return None

    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding pair: {str(e)}")
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

    while True:
        try:
            async with websockets.connect(
                uri,
                extra_headers=headers,
                ssl=ssl_context,
                max_size=None,
            ) as websocket:
                while True:
                    try:
                        message = await websocket.recv()

                        if DEBUG:
                            logger.info(f"Received message ({len(message)} bytes)")

                        if message == "ping":
                            await websocket.send("pong")
                            continue

                        if isinstance(message, bytes):
                            if not message.startswith(b'\x00\n1.3.0\n'):
                                continue

                            pairs_start = message.find(b'pairs')
                            if pairs_start == -1:
                                continue

                            pairs = []
                            pos = pairs_start + 5
                            while pos < len(message):
                                pair = decode_pair(message[pos:pos+512])
                                if pair:
                                    pairs.append(pair)
                                pos += 512

                            if pairs:
                                print(json.dumps({"type": "pairs", "pairs": pairs}, indent=None))

                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception as e:
                        if DEBUG:
                            logger.error(f"Error processing message: {str(e)}")
                        continue

        except Exception as e:
            if DEBUG:
                logger.error(f"Connection error: {str(e)}")
            await asyncio.sleep(1)

async def main():
    while True:
        try:
            await connect_to_dexscreener()
        except Exception as e:
            if DEBUG:
                logger.error(f"Main loop error: {str(e)}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
