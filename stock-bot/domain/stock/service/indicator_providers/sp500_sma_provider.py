import json
import pandas as pd

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class Sp500SmaProvider(BaseIndicatorProvider):
    """
    DB에 저장된 S&P 500 데이터를 기반으로 200일 이동 평균(SMA)을 계산하고 저장하는 책임을 가집니다.
    """

    def __init__(self, window: int = 200):
        super().__init__()
        self.window = window
        self.indicator_type = MarketIndicatorType.SP500_SMA_200

    def update(self) -> bool:
        logger.info(f"Starting S&P 500 {self.window}-day SMA calculation...")
        try:
            sp500_data = self.repository.get_recent_market_data(MarketIndicatorType.SP500_INDEX, limit=self.window + 50)
            if len(sp500_data) < self.window:
                logger.warning(f"Not enough S&P 500 data to calculate {self.window}-day SMA. Found {len(sp500_data)} points.")
                return False

            df = pd.DataFrame([(d.date, d.value) for d in sp500_data], columns=['Date', 'Close']).set_index('Date')
            df.sort_index(inplace=True)

            sma_series = df['Close'].rolling(window=self.window).mean().dropna()
            if sma_series.empty:
                logger.warning("SMA calculation resulted in an empty series.")
                return False

            for sma_date, sma_value in sma_series.tail(5).items():
                additional_data = json.dumps({
                    "data_source": "Calculated from SP500_INDEX in DB",
                    "calculation_window": self.window
                })
                self.repository.save_market_data(
                    indicator_type=self.indicator_type,
                    data_date=sma_date,
                    value=sma_value,
                    additional_data=additional_data
                )
            logger.info(f"Successfully updated S&P 500 {self.window}-day SMA.")
            return True
        except Exception as e:
            logger.error(f"Error calculating S&P 500 SMA: {e}", exc_info=True)
            return False
