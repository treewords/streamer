import json
import logging
import asyncio
import websockets
import gzip
import io
from datetime import datetime
from typing import Callable, Awaitable, Optional

from .models import Config, Candle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class BingxStreamer:
    def __init__(
        self,
        config: Config,
        on_candle_update: Optional[Callable[[Candle], Awaitable[None]]] = None,
        on_candle_close: Optional[Callable[[Candle], Awaitable[None]]] = None,
    ):
        self.config = config
        self.on_candle_update = on_candle_update
        self.on_candle_close = on_candle_close
        self.current_candle_timestamp = None
        self.last_candle_update: Candle | None = None

    async def start(self):
        async with websockets.connect(self.config.URL) as ws:
            logging.info('WebSocket connected')
            sub_str = json.dumps(self.config.SUBSCRIPTION)
            await ws.send(sub_str)
            logging.info("Subscribed to: %s", sub_str)

            async for message in ws:
                try:
                    compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
                    decompressed_data = compressed_data.read()
                    utf8_data = decompressed_data.decode('utf-8')

                    if utf8_data == "Ping":
                        await ws.send("Pong")
                        continue

                    data = json.loads(utf8_data)

                    if data.get('dataType') == self.config.SUBSCRIPTION['dataType'] and data.get('data'):
                        for candle_data in data['data']:
                            if all(k in candle_data for k in ('T', 'o', 'h', 'l', 'c', 'v')):
                                candle_timestamp = datetime.fromtimestamp(candle_data['T'] / 1000)

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
                                    if self.on_candle_update:
                                        await self.on_candle_update(current_candle)
                                    continue

                                if candle_timestamp > self.current_candle_timestamp:
                                    closed_candle = self.last_candle_update
                                    logging.info(
                                        f"Candle closed at {self.current_candle_timestamp}: "
                                        f"O={closed_candle.open}, H={closed_candle.high}, "
                                        f"L={closed_candle.low}, C={closed_candle.close}, V={closed_candle.volume}"
                                    )
                                    if self.on_candle_close:
                                        await self.on_candle_close(closed_candle)

                                    self.current_candle_timestamp = candle_timestamp

                                self.last_candle_update = current_candle
                                if self.on_candle_update:
                                    await self.on_candle_update(current_candle)
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
