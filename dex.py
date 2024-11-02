import asyncio
import websockets
import json
import ssl

async def connect_to_dexscreener():
    uri = "wss://io.dexscreener.com/dex/screener/v4/pairs/h24/1?rankBy[key]=trendingScoreH6&rankBy[order]=desc&filters[chainIds][0]=solana" #"wss://io.dexscreener.com/dex/screener/pairs/h24/1?rankBy[key]=trendingScoreH24&rankBy[order]=desc"
    
    # Headers with the specific User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Origin': 'https://dexscreener.com'
    }

    try:
        async with websockets.connect(uri, extra_headers=headers, ssl=ssl.create_default_context()) as websocket:
            print("Connected to DexScreener WebSocket")
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received: {json.dumps(data, indent=2)}")
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"Failed to connect. Status code: {e.status_code}")
        print(f"Response headers: {e.headers}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

async def main():
    await connect_to_dexscreener()

if __name__ == "__main__":
    asyncio.run(main())