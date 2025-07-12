# domain/market_data_backfiller/providers/yahoo_provider.py
from datetime import date
import yfinance as yf

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class YahooBackfillProvider(BaseBackfillProvider):
    """Yahoo Finance에서 데이터를 가져와 백필합니다."""

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> bool:
        logger.info(f"Backfilling {self.indicator_type.value} ({self.symbol}) from Yahoo Finance for {start_date} to {end_date}...")
        try:
            df = yf.download(self.symbol, start=start_date, end=end_date, progress=False)
            if df.empty:
                logger.warning(f"No data received from Yahoo Finance for {self.symbol}.")
                return False

            saved_count = 0
            for data_date, row in df.iterrows():
                success = self.repository.save_market_data(
                    indicator_type=self.indicator_type,
                    data_date=data_date.date(),
                    value=row['Close']
                )
                if success:
                    saved_count += 1
            
            logger.info(f"Successfully saved {saved_count} data points for {self.indicator_type.value}.")
            return True
        except Exception as e:
            logger.error(f"Failed to backfill {self.indicator_type.value}: {e}", exc_info=True)
            return False
