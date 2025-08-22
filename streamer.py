import json
import logging
import asyncio
import websockets
import gzip
import io
import pandas as pd
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

URL = "wss://open-api-swap.bingx.com/swap-market"

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class BingxStreamer:
    def __init__(self, symbol: str, timeframe: str):
        self.url = URL
        self.symbol = symbol
        self.timeframe = timeframe
        self.subscription = {
            "id": f"{symbol}-{timeframe}-{datetime.now().timestamp()}",
            "reqType": "sub",
            "dataType": f"{self.symbol}@kline_{self.timeframe}"
        }
        self.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.current_candle_timestamp = None
        self.last_candle_update: Candle | None = None

    async def start(self):
        async with websockets.connect(self.url) as ws:
            logging.info('WebSocket connected')
            sub_str = json.dumps(self.subscription)
            await ws.send(sub_str)
            logging.info("Subscribed to: %s", sub_str)

            async for message in ws:
                try:
                    # Decompress the message
                    compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
                    decompressed_data = compressed_data.read()
                    utf8_data = decompressed_data.decode('utf-8')

                    if utf8_data == "Ping":
                        await ws.send("Pong")
                        continue

                    data = json.loads(utf8_data)

                    if data.get('dataType') == self.subscription['dataType'] and data.get('data'):
                        for candle_data in data['data']:
                            if all(k in candle_data for k in ('T', 'o', 'h', 'l', 'c', 'v')):
                                candle_timestamp = pd.to_datetime(candle_data['T'], unit='ms')

                                current_candle = Candle(
                                    timestamp=candle_timestamp,
                                    open=float(candle_data['o']),
                                    high=float(candle_data['h']),
                                    low=float(candle_data['l']),
                                    close=float(candle_data['c']),
                                    volume=float(candle_data['v'])
                                )

                                if self.current_candle_timestamp is None:
                                    self.current_candle_timestamp = candle_timestamp
                                    self.last_candle_update = current_candle
                                    continue

                                if candle_timestamp > self.current_candle_timestamp:
                                    closed_candle = self.last_candle_update
                                    logging.info(
                                        f"Candle closed at {self.current_candle_timestamp}: "
                                        f"O={closed_candle.open}, H={closed_candle.high}, "
                                        f"L={closed_candle.low}, C={closed_candle.close}, V={closed_candle.volume}"
                                    )

                                    new_row = {
                                        'timestamp': closed_candle.timestamp,
                                        'open': closed_candle.open,
                                        'high': closed_candle.high,
                                        'low': closed_candle.low,
                                        'close': closed_candle.close,
                                        'volume': closed_candle.volume,
                                    }
                                    self.df.loc[len(self.df)] = new_row
                                    self.current_candle_timestamp = candle_timestamp

                                self.last_candle_update = current_candle
                            else:
                                logging.debug("Received object in kline data stream with unexpected structure: %s", candle_data)
                    elif 'code' in data and data['code'] == 0:
                        logging.info("Received subscription confirmation: %s", utf8_data)
                    else:
                        logging.debug("Received non-kline message: %s", utf8_data)

                except (json.JSONDecodeError, TypeError) as e:
                    logging.error("Failed to process message: %s. Error: %s", utf8_data, e)
                except Exception as e:
                    logging.error("An unexpected error occurred: %s", e)


if __name__ == "__main__":
    # Example usage:
    symbol = "BTC-USDT"
    timeframe = "1m"  # e.g., 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w

    streamer = BingxStreamer(symbol=symbol, timeframe=timeframe)
    try:
        logging.info(f"Starting streamer for {symbol} with timeframe {timeframe}")
        asyncio.run(streamer.start())
    except KeyboardInterrupt:
        logging.info("Streamer stopped by user.")
    except Exception as e:
        logging.error("Streamer failed: %s", e)
