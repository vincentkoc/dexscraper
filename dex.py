import asyncio
import websockets
import json
import ssl
import logging
from datetime import datetime
import urllib.parse
import struct
from decimal import Decimal, ROUND_DOWN

DEBUG = True  # Set to False for production

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_number(value):
    """Format numbers with appropriate precision"""
    try:
        if not isinstance(value, (int, float)) or value == 0:
            return "0"

        # Handle very small numbers
        if abs(value) < 0.00000001:
            return f"{value:.12f}".rstrip('0').rstrip('.')

        # Handle very large numbers
        if abs(value) > 1e12:
            return str(int(value))

        # Handle negative numbers
        if value < 0:
            return f"-{format_number(abs(value))}"

        # Handle regular decimal numbers
        d = Decimal(str(value))
        return str(d.normalize()).rstrip('0').rstrip('.')

    except:
        return "0"

def decode_metrics(data, start_pos):
    """Decode numeric values from binary data"""
    try:
        if start_pos + 64 > len(data):
            return {}, start_pos

        metrics = {}
        doubles = struct.unpack('8d', data[start_pos:start_pos+64])

        # Only filter out extreme invalid values
        if -1e308 < doubles[0] < 1e308:
            metrics['price'] = doubles[0]
        if -1e308 < doubles[1] < 1e308:
            metrics['priceUsd'] = doubles[1]
        if -1e308 < doubles[2] < 1e308:
            metrics['priceChangeH24'] = doubles[2]
        if -1e308 < doubles[3] < 1e308:
            metrics['liquidityUsd'] = doubles[3]
        if -1e308 < doubles[4] < 1e308:
            metrics['volumeH24'] = doubles[4]
        if -1e308 < doubles[5] < 1e308:
            metrics['fdv'] = doubles[5]
        if doubles[6] >= 0 and doubles[6] < 1e10:
            metrics['timestamp'] = doubles[6]

        return metrics, start_pos + 64
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
            if 'price' in metrics:
                pair['price'] = format_number(metrics['price'])
            if 'priceUsd' in metrics:
                pair['priceUsd'] = format_number(metrics['priceUsd'])
            if 'priceChangeH24' in metrics:
                pair['priceChange'] = {'h24': format_number(metrics['priceChangeH24'])}
            if 'liquidityUsd' in metrics:
                pair['liquidity'] = {'usd': format_number(metrics['liquidityUsd'])}
            if 'volumeH24' in metrics:
                pair['volume'] = {'h24': format_number(metrics['volumeH24'])}
            if 'fdv' in metrics:
                pair['fdv'] = format_number(metrics['fdv'])

            if 'timestamp' in metrics:
                pair['pairCreatedAt'] = int(metrics['timestamp'])
                try:
                    pair['pairCreatedAtFormatted'] = datetime.fromtimestamp(pair['pairCreatedAt']).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pair['pairCreatedAtFormatted'] = "1970-01-01 00:00:00"

        # Only return pairs with valid data
        if any(key in pair for key in ['price', 'priceUsd', 'volume', 'liquidity']) and any(pair.values()):
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
                            if DEBUG:
                                logger.info("Sent pong response")
                            continue

                        if isinstance(message, bytes):
                            # Skip version check
                            if not message.startswith(b'\x00\n1.3.0\n'):
                                continue

                            # Find pairs data
                            pairs_start = message.find(b'pairs')
                            if pairs_start == -1:
                                continue

                            # Process pairs in chunks
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
            continue

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
