from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class Config:
    URL: str = "wss://open-api-swap.bingx.com/swap-market"
    SYMBOL: str = "BTC-USDT"
    TIMEFRAME: str = "1m"
    SUBSCRIPTION: Dict = field(init=False)

    def __post_init__(self):
        self.SUBSCRIPTION = {
            "id": f"{self.SYMBOL}-{self.TIMEFRAME}-{datetime.now().timestamp()}",
            "reqType": "sub",
            "dataType": f"{self.SYMBOL}@kline_{self.TIMEFRAME}"
        }

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
