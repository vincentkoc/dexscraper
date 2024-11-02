import asyncio
import websockets
import json
import ssl
import logging
from datetime import datetime
import urllib.parse
import struct

DEBUG = True

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def decode_pair_data(data, start_pos):
    try:
        pair = {}

        # Read chain
        chain_len = data[start_pos]
        start_pos += 1
        pair['chain'] = data[start_pos:start_pos+chain_len].decode('utf-8')
        start_pos += chain_len

        # Read protocol
        protocol_len = data[start_pos]
        start_pos += 1
        pair['protocol'] = data[start_pos:start_pos+protocol_len].decode('utf-8')
        start_pos += protocol_len

        # Read pair address
        pair_addr_len = data[start_pos]
        start_pos += 1
        pair['pairAddress'] = data[start_pos:start_pos+pair_addr_len].decode('utf-8')
        start_pos += pair_addr_len

        # Read token name
        token_name_len = data[start_pos]
        start_pos += 1
        pair['baseTokenName'] = data[start_pos:start_pos+token_name_len].decode('utf-8')
        start_pos += token_name_len

        # Read token symbol
        token_symbol_len = data[start_pos]
        start_pos += 1
        pair['baseTokenSymbol'] = data[start_pos:start_pos+token_symbol_len].decode('utf-8')
        start_pos += token_symbol_len

        # Read token address
        token_addr_len = data[start_pos]
        start_pos += 1
        pair['baseTokenAddress'] = data[start_pos:start_pos+token_addr_len].decode('utf-8')
        start_pos += token_addr_len

        # Read prices and metrics (packed as doubles)
        metrics = struct.unpack('8d', data[start_pos:start_pos+64])
        pair['price'] = metrics[0]
        pair['priceUsd'] = metrics[1]
        pair['priceChange'] = {'h24': metrics[2]}
        pair['liquidity'] = {'usd': metrics[3]}
        pair['volume'] = {'h24': metrics[4]}
        pair['fdv'] = metrics[5]

        # Read timestamps
        pair['pairCreatedAt'] = int(metrics[6])
        pair['pairCreatedAtFormatted'] = datetime.fromtimestamp(metrics[6]).strftime('%Y-%m-%d %H:%M:%S')

        return pair, start_pos + 64
    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding pair: {str(e)}")
        return None, start_pos

def decode_binary_message(binary_data):
    try:
        if not binary_data.startswith(b'\x00\n1.3.0\n'):
            return None

        data_start = binary_data.find(b'pairs')
        if data_start == -1:
            return None

        pos = data_start + 5  # Skip "pairs"
        pairs = []

        while pos < len(binary_data):
            try:
                pair, new_pos = decode_pair_data(binary_data, pos)
                if pair:
                    pairs.append(pair)
                pos = new_pos
            except:
                break

        return {
            "type": "pairs",
            "pairs": pairs
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding binary message: {str(e)}")
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

    try:
        if DEBUG:
            logger.info(f"Attempting to connect to {uri}")

        async with websockets.connect(
            uri,
            extra_headers=headers,
            ssl=ssl_context,
            max_size=None,
        ) as websocket:
            if DEBUG:
                logger.info("Successfully connected to DexScreener WebSocket")

            while True:
                try:
                    message = await websocket.recv()

                    if DEBUG:
                        if isinstance(message, bytes):
                            logger.info(f"Received binary message ({len(message)} bytes)")

                    # Handle ping messages
                    if message == "ping":
                        if DEBUG:
                            logger.info("Received ping, sending pong")
                        await websocket.send("pong")
                        continue

                    # Handle binary messages
                    if isinstance(message, bytes):
                        data = decode_binary_message(message)
                        if data and data.get('pairs'):
                            print(json.dumps(data, indent=2))

                except websockets.exceptions.ConnectionClosed:
                    if DEBUG:
                        logger.warning("Connection closed")
                    break
                except Exception as e:
                    if DEBUG:
                        logger.error(f"Error: {str(e)}")
                    continue

    except websockets.exceptions.InvalidStatusCode as e:
        if DEBUG:
            logger.error(f"Failed to connect. Status code: {e.status_code}")
    except Exception as e:
        if DEBUG:
            logger.error(f"An error occurred: {str(e)}")
        raise

async def main():
    while True:
        try:
            if DEBUG:
                logger.info("Starting connection")
            await connect_to_dexscreener()
        except Exception as e:
            if DEBUG:
                logger.error(f"Connection failed: {str(e)}")
            logger.info("Reconnecting in 1 second...")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
