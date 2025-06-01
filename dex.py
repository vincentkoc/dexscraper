import asyncio
import websockets
import json
import ssl
import logging
from datetime import datetime
import urllib.parse
import struct
from decimal import Decimal, ROUND_DOWN

DEBUG = False

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_double(value):
    """Handle potential NaN/Inf values"""
    try:
        if not isinstance(value, float) or value != value or abs(value) == float('inf'):
            return 0
        return value
    except:
        return 0

def decode_metrics(data, start_pos):
    """Decode numeric values from binary data"""
    try:
        if start_pos + 64 > len(data):
            return {}, start_pos

        metrics = {}
        values = struct.unpack('8d', data[start_pos:start_pos+64])

        # Map metrics with validation
        value_map = {
            'price': values[0],
            'priceUsd': values[1],
            'priceChangeH24': values[2],
            'liquidityUsd': values[3],
            'volumeH24': values[4],
            'fdv': values[5],
            'timestamp': values[6]
        }

        # Validate and clean each value
        for key, value in value_map.items():
            cleaned = handle_double(value)
            if cleaned != 0:
                metrics[key] = cleaned

        return metrics, start_pos + 64

    except:
        return {}, start_pos

def clean_string(s):
    """Clean invalid and control characters from strings"""
    try:
        if not s:
            return ""
        # Remove non-printable characters except spaces
        cleaned = ''.join(char for char in s if (32 <= ord(char) < 127) or ord(char) == 9)

        # Filter out common garbage patterns
        if '@' in cleaned or '\\' in cleaned:
            return cleaned.split('@')[0].split('\\')[0]

        return cleaned.strip()
    except:
        return ""

def decode_pair(data):
    """Decode a single trading pair from binary data"""
    try:
        pos = 0
        pair = {}

        # Skip any binary prefix
        while pos < len(data) and data[pos] in (0x00, 0x0A):
            pos += 1

        # Read string fields
        fields = ['chain', 'protocol', 'pairAddress', 'baseTokenName',
                 'baseTokenSymbol', 'baseTokenAddress']

        for field in fields:
            if pos >= len(data):
                break

            str_len = data[pos]
            pos += 1

            # If the declared length looks unreasonable or extends past the
            # available data, stop parsing this pair to avoid misalignment.
            if str_len > 100 or pos + str_len > len(data):
                break

            if str_len == 0:
                continue

            value = clean_string(data[pos:pos+str_len].decode('utf-8', errors='ignore'))
            if value:
                pair[field] = value
            pos += str_len

        # Align to 8-byte boundary for doubles
        pos = (pos + 7) & ~7

        # Read and format metrics
        metrics, pos = decode_metrics(data, pos)

        if metrics:
            # Format price/volume numbers
            if 'price' in metrics:
                pair['price'] = str(metrics['price'])
            if 'priceUsd' in metrics:
                pair['priceUsd'] = str(metrics['priceUsd'])
            if 'priceChangeH24' in metrics:
                pair['priceChange'] = {'h24': str(metrics['priceChangeH24'])}
            if 'liquidityUsd' in metrics:
                pair['liquidity'] = {'usd': str(metrics['liquidityUsd'])}
            if 'volumeH24' in metrics:
                pair['volume'] = {'h24': str(metrics['volumeH24'])}
            if 'fdv' in metrics:
                pair['fdv'] = str(metrics['fdv'])

            # Handle timestamp
            if 'timestamp' in metrics and 0 <= metrics['timestamp'] < 4102444800:
                pair['pairCreatedAt'] = int(metrics['timestamp'])
                try:
                    pair['pairCreatedAtFormatted'] = datetime.fromtimestamp(
                        pair['pairCreatedAt']
                    ).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pair['pairCreatedAtFormatted'] = "1970-01-01 00:00:00"

        # Validate the pair has minimum required data
        if len(pair) > 2 and any(v != '0' for v in [
            pair.get('price'),
            pair.get('priceUsd'),
            pair.get('volume', {}).get('h24'),
            pair.get('liquidity', {}).get('usd')
        ]):
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
