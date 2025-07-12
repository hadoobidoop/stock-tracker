# domain/market_data_backfiller/providers/fred_provider.py
import json
from datetime import date
from typing import List, Dict, Any
import pandas as pd
import pandas_datareader.data as web

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FredBackfillProvider(BaseBackfillProvider):
    """FRED(Federal Reserve Economic Data)에서 데이터를 가져와 파싱합니다."""

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        logger.info(f"Fetching {self.indicator_type.value} ({self.symbol}) from FRED for {start_date} to {end_date}...")
        
        df = web.DataReader(self.symbol, 'fred', start_date, end_date)
        if df.empty:
            logger.warning(f"No data received from FRED for {self.symbol}.")
            return []

        records = []
        for data_date, row in df.iterrows():
            if pd.notna(row[self.symbol]):
                records.append({
                    "indicator_type": self.indicator_type.value,
                    "date": data_date.date(),
                    "value": row[self.symbol].item(),
                    "additional_data": json.dumps({"data_source": f"FRED ({self.symbol})"})
                })
        
        logger.info(f"Successfully parsed {len(records)} data points for {self.indicator_type.value}.")
        return records

