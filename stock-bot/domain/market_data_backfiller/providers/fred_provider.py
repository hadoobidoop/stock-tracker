# domain/market_data_backfiller/providers/fred_provider.py
from datetime import date
import pandas as pd
import pandas_datareader.data as web

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FredBackfillProvider(BaseBackfillProvider):
    """FRED(Federal Reserve Economic Data)에서 데이터를 가져와 백필합니다."""

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> bool:
        logger.info(f"Backfilling {self.indicator_type.value} ({self.symbol}) from FRED for {start_date} to {end_date}...")
        try:
            df = web.DataReader(self.symbol, 'fred', start_date, end_date)
            if df.empty:
                logger.warning(f"No data received from FRED for {self.symbol}.")
                return False

            saved_count = 0
            for data_date, row in df.iterrows():
                value = row[self.symbol]
                if pd.notna(value):
                    success = self.repository.save_market_data(
                        indicator_type=self.indicator_type,
                        data_date=data_date.date(),
                        value=value.item()
                    )
                    if success:
                        saved_count += 1
            
            logger.info(f"Successfully saved {saved_count} data points for {self.indicator_type.value}.")
            return True
        except Exception as e:
            logger.error(f"Failed to backfill {self.indicator_type.value}: {e}", exc_info=True)
            return False
