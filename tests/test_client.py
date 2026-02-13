import asyncio
import io
import logging
import unittest
import json
import gzip
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import importlib

class TestBingxStreamer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Setup logging capture
        self.log_stream = io.StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.handler)
        # We need to capture ERROR logs to verify them
        self.logger.setLevel(logging.ERROR)

        # Create mock for websockets
        self.mock_websockets = MagicMock()

        # Apply patch to sys.modules
        # We patch 'websockets' so that when client is imported, it uses this mock
        self.modules_patcher = patch.dict(sys.modules, {'websockets': self.mock_websockets})
        self.modules_patcher.start()

        # Ensure bingx_streamer.client is imported using the mocked websockets
        # If it was already imported, we need to reload it or delete it from sys.modules
        if 'bingx_streamer.client' in sys.modules:
             del sys.modules['bingx_streamer.client']

        import bingx_streamer.client
        self.client_module = bingx_streamer.client
        self.BingxStreamer = self.client_module.BingxStreamer

        # Config is safe to import normally as it has no external deps
        from bingx_streamer.models import Config
        self.Config = Config

    async def asyncTearDown(self):
        self.logger.removeHandler(self.handler)
        self.log_stream.close()
        self.modules_patcher.stop()

    async def test_start_malformed_json_logging(self):
        """Test that malformed JSON triggers the expected error log."""

        # Prepare malformed JSON data (valid GZIP, invalid JSON)
        malformed_json_str = "not a json string"
        malformed_json_bytes = malformed_json_str.encode('utf-8')

        # Compress it
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as f:
            f.write(malformed_json_bytes)
        compressed_malformed = out.getvalue()

        # Create a mock websocket connection context manager
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        mock_connect_ctx = MagicMock()
        self.mock_websockets.connect.return_value = mock_connect_ctx
        mock_connect_ctx.__aenter__.return_value = mock_ws

        # Setup async iteration via return_value list (MagicMock wraps this automatically)
        mock_ws.__aiter__.return_value = [compressed_malformed]

        config = self.Config()
        streamer = self.BingxStreamer(config)

        # Run the streamer start method
        await streamer.start()

        # Check logs
        log_output = self.log_stream.getvalue()
        self.assertIn("Failed to process message:", log_output)
        self.assertIn(malformed_json_str, log_output) # verify the data is logged
        self.assertIn("Error:", log_output)

    async def test_start_invalid_gzip_logging(self):
        """Test that invalid GZIP data triggers the expected error log."""

        # Prepare invalid GZIP data (just random bytes)
        invalid_gzip = b"random junk data"

        # Create a mock websocket connection context manager
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        mock_connect_ctx = MagicMock()
        self.mock_websockets.connect.return_value = mock_connect_ctx
        mock_connect_ctx.__aenter__.return_value = mock_ws

        # Setup async iteration via return_value list
        mock_ws.__aiter__.return_value = [invalid_gzip]

        config = self.Config()
        streamer = self.BingxStreamer(config)

        # Run the streamer start method
        await streamer.start()

        # Check logs
        log_output = self.log_stream.getvalue()
        # Since invalid gzip is likely to raise an OSError or similar, it should be caught by "except Exception"
        self.assertIn("An unexpected error occurred:", log_output)

    async def test_valid_message(self):
        """Test that a valid message is processed without error."""

        # Prepare valid JSON data
        valid_data = {
            "code": 0,
            "data": [{"T": 1678886400000, "o": 20000, "h": 21000, "l": 19000, "c": 20500, "v": 100}],
            "dataType": "BTC-USDT@kline_1m"
        }
        valid_json_str = json.dumps(valid_data)
        valid_json_bytes = valid_json_str.encode('utf-8')

        # Compress it
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as f:
            f.write(valid_json_bytes)
        compressed_valid = out.getvalue()

        # Mock setup
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        mock_connect_ctx = MagicMock()
        self.mock_websockets.connect.return_value = mock_connect_ctx
        mock_connect_ctx.__aenter__.return_value = mock_ws

        # Setup async iteration via return_value list
        mock_ws.__aiter__.return_value = [compressed_valid]

        config = self.Config(SYMBOL="BTC-USDT", TIMEFRAME="1m")
        streamer = self.BingxStreamer(config)

        # Run
        await streamer.start()

        # Check logs - expect NO errors
        log_output = self.log_stream.getvalue()
        self.assertEqual(log_output, "")

if __name__ == '__main__':
    unittest.main()
