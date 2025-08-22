import asyncio
import logging
import pandas as pd

from bingx_streamer import BingxStreamer, Config, Candle

# --- Optional: Setup pandas DataFrame for data storage ---
# This is just one example of what you can do in a callback.
# You could also write to a database, a CSV file, or trigger alerts.
df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df.set_index('timestamp', inplace=True)

# --- Define Your Callbacks ---
async def on_candle_close(candle: Candle):
    """
    This function is called whenever a candle closes.
    """
    logging.info(f"CALLBACK: New candle closed: {candle}")

    # Example: Append the closed candle to a pandas DataFrame
    new_row = {
        'timestamp': candle.timestamp,
        'open': candle.open,
        'high': candle.high,
        'low': candle.low,
        'close': candle.close,
        'volume': candle.volume,
    }
    # Using .loc to append a new row
    df.loc[candle.timestamp] = new_row

    # Print the latest state of the DataFrame
    logging.info(f"Current DataFrame:\n{df.tail(5)}")

async def on_candle_update(candle: Candle):
    """
    This function is called whenever a candle is updated (including the initial one).
    """
    # This callback can be used for real-time monitoring of the current (incomplete) candle.
    # For this example, we'll just log it.
    logging.info(f"CALLBACK: Candle updated: C={candle.close}, V={candle.volume}")


# --- Main Execution ---
async def main():
    """
    Main function to set up and run the streamer.
    """
    logging.info("Starting streamer application...")

    # 1. Configure the streamer
    # You can change the symbol and timeframe here
    config = Config(SYMBOL="BTC-USDT", TIMEFRAME="1m")

    # 2. Instantiate the streamer with your callbacks
    streamer = BingxStreamer(
        config=config,
        on_candle_close=on_candle_close,
        on_candle_update=on_candle_update
    )

    # 3. Start the streamer
    # The start() method runs indefinitely until an exception occurs or the program is stopped.
    try:
        logging.info(f"Connecting to stream for {config.SYMBOL} ({config.TIMEFRAME})...")
        await streamer.start()
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")
    except Exception as e:
        logging.error(f"Application failed: {e}", exc_info=True)
