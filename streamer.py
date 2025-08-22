import json
import logging
import websocket
import gzip
import io
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

URL="wss://open-api-swap.bingx.com/swap-market"
CHANNEL= {"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@kline_3m"}
class Test(object):

    def __init__(self):
        self.url = URL
        self.ws = None
        self.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    def on_open(self, ws):
        logging.info('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        logging.info("Subscribed to: %s", subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        logging.debug("Received data: %s", utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')

        if utf8_data == "Ping":
           ws.send("Pong")
           return

        try:
            data = json.loads(utf8_data)
            if data.get('dataType') == 'BTC-USDT@kline_3m' and data.get('data'):
                for candle in data['data']:
                    if all(k in candle for k in ('T', 'o', 'h', 'l', 'c', 'v')):
                        new_candle = {
                            'timestamp': pd.to_datetime(candle['T'], unit='ms'),
                            'open': float(candle['o']),
                            'high': float(candle['h']),
                            'low': float(candle['l']),
                            'close': float(candle['c']),
                            'volume': float(candle['v'])
                        }

                        new_df = pd.DataFrame([new_candle])
                        self.df = pd.concat([self.df, new_df], ignore_index=True)

                        logging.info(f"New 3-min candle close: {new_candle['close']} at {new_candle['timestamp']}")
                    else:
                        logging.debug("Received object in kline data stream with unexpected structure: %s", candle)
            else:
                if 'code' in data and data['code'] == 0:
                    logging.info("Received subscription confirmation: %s", utf8_data)
                else:
                    logging.debug("Received non-kline message: %s", utf8_data)
        except (json.JSONDecodeError, TypeError):
            logging.error("Failed to process message: %s", utf8_data)

    def on_error(self, ws, error):
        logging.error(error)

    def on_close(self, ws, close_status_code, close_msg):
        logging.warning('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
