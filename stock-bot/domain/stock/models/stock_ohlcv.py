
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass
class StockOhlcv:
    """
    시가, 고가, 저가, 종가, 거래량(OHLCV) 및 관련 기술적 지표를 나타내는 도메인 모델.
    """
    ticker: str
    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str = '1m'
    indicators: Dict[str, Any] = field(default_factory=dict)

