# domain/market_data_backfiller/providers/yahoo_provider.py
import json
from datetime import date
from typing import List, Dict, Any
import yfinance as yf

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class YahooBackfillProvider(BaseBackfillProvider):
    """Yahoo Finance에서 데이터를 가져와 파싱합니다."""

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        logger.info(f"Fetching {self.indicator_type.value} ({self.symbol}) from Yahoo Finance for {start_date} to {end_date}...")
        
        df = yf.download(self.symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            logger.warning(f"No data received from Yahoo Finance for {self.symbol}.")
            return []

        records = []
        for data_date, row in df.iterrows():
            records.append({
                "indicator_type": self.indicator_type.value,
                "date": data_date.date(),
                "value": row['Close'],
                "additional_data": json.dumps({"data_source": f"Yahoo Finance ({self.symbol})"})
            })
            
        logger.info(f"Successfully parsed {len(records)} data points for {self.indicator_type.value}.")
        return records

