# BingX WebSocket Streamer

A small and extensible Python library for streaming candlestick data from the BingX Swap API via WebSockets.

This library is designed to be lightweight and flexible, allowing you to easily integrate real-time market data into your applications. It uses an asynchronous, callback-based approach to handle incoming data.

## Features

- Connects to the BingX public swap market WebSocket API.
- Subscribes to candlestick (k-line) data for any symbol and timeframe.
- Handles WebSocket ping/pong and GZIP decompression automatically.
- Extensible callback system: provides `on_candle_update` and `on_candle_close` hooks.
- Lightweight core with minimal dependencies.

## Installation

You can install the library directly from this repository:

```bash
pip install .
```

To run the example, which uses pandas for data handling, install the `examples` extras:

```bash
pip install .[examples]
```

## Usage

Here is a quick example of how to use the library. See `run_streamer.py` for a more detailed example.

```python
import asyncio
import logging
from bingx_streamer import BingxStreamer, Config, Candle

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define your callback function
async def handle_closed_candle(candle: Candle):
    print(f"New candle closed: {candle.symbol} @ {candle.close}")

# Set up the configuration
config = Config(SYMBOL="BTC-USDT", TIMEFRAME="1m")

# Create a streamer instance
streamer = BingxStreamer(config, on_candle_close=handle_closed_candle)

# Run the streamer
try:
    asyncio.run(streamer.start())
except KeyboardInterrupt:
    print("Streamer stopped.")
```

## How It Works

The `BingxStreamer` connects to the WebSocket and handles the subscription and data decompression. When a candle closes (i.e., a new candle for the next timeframe arrives), it triggers the `on_candle_close` callback with the completed `Candle` object. The `on_candle_update` callback is triggered for every single update, including the initial one.

This allows you to decouple your data processing logic from the streaming client itself. You can write the data to a database, perform calculations, or trigger other events from within your callbacks.
