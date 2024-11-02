import asyncio
import websockets
import json
import ssl
import logging
import base64
import os
import struct
from datetime import datetime
import urllib.parse

DEBUG = True

logging.basicConfig(
    level=logging.INFO if DEBUG else logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def decode_latest_block(data):
    try:
        # Skip header
        pos = data.find(b'latestBlock') + len(b'latestBlock')
        # Next 16 bytes contain two double values
        block_num, timestamp = struct.unpack('dd', data[pos:pos+16])
        return {
            "type": "latestBlock",
            "blockNumber": block_num,
            "timestamp": timestamp
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding latest block: {str(e)}")
        return None

def decode_pairs(data):
    try:
        pairs = []
        pos = data.find(b'pairs') + len(b'pairs')
        
        # First 8 doubles are metrics
        metrics = struct.unpack('8d', data[pos:pos+64])
        pos += 64

        while pos < len(data):
            # Read length of chain
            chain_len = data[pos]
            pos += 1
            if chain_len == 0:
                break

            # Read chain
            chain = data[pos:pos+chain_len].decode('utf-8')
            pos += chain_len

            # Read length of protocol
            protocol_len = data[pos]
            pos += 1
            if protocol_len == 0:
                break

            # Read protocol
            protocol = data[pos:pos+protocol_len].decode('utf-8')
            pos += protocol_len

            pair = {
                "chain": chain,
                "protocol": protocol,
                "metrics": {
                    "price": metrics[0],
                    "priceChange": metrics[1],
                    "liquidity": metrics[2],
                    "volume": metrics[3],
                    "txns": metrics[4],
                    "score": metrics[5]
                }
            }
            pairs.append(pair)

        return {
            "type": "pairs",
            "pairs": pairs
        }
    except Exception as e:
        if DEBUG:
            logger.error(f"Error decoding pairs: {str(e)}")
        return None

async def connect_to_dexscreener():
    base_uri = "wss://io.dexscreener.com/dex/screener/v4/pairs/h24/1"
    params = {
        "rankBy[key]": "trendingScoreH6",
        "rankBy[order]": "desc",
        "filters[chainIds][0]": "solana"
    }
    uri = f"{base_uri}?{urllib.parse.urlencode(params)}"
    
    ws_key = base64.b64encode(os.urandom(16)).decode()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-WebSocket-Version': '13',
        'Origin': 'https://dexscreener.com',
        'Sec-WebSocket-Key': ws_key,
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

                    # Handle ping messages
                    if message == "ping":
                        if DEBUG:
                            logger.info("Received ping, sending pong")
                        await websocket.send("pong")
                        continue

                    # Handle binary messages
                    if isinstance(message, bytes):
                        # Skip first two bytes (message type and newline)
                        if not message.startswith(b'\x00\n') and not message.startswith(b'\x02\n'):
                            continue

                        # Skip version string
                        pos = message.find(b'\n', 2) + 1
                        
                        if b'latestBlock' in message:
                            data = decode_latest_block(message[pos:])
                            if data:
                                print(json.dumps(data, indent=None))
                        elif b'pairs' in message:
                            data = decode_pairs(message[pos:])
                            if data:
                                print(json.dumps(data, indent=None))
                    
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