import json
from datetime import datetime, timedelta
import pandas as pd
import pandas_datareader.data as web

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FredProvider(BaseIndicatorProvider):
    """
    FRED(Federal Reserve Economic Data)에서 단일 심볼 데이터를 가져오는 책임을 가집니다.
    """

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type

    def update(self) -> bool:
        logger.info(f"Starting {self.indicator_type.value} update from FRED (symbol: {self.symbol})...")
        try:
            start_date = datetime.now() - timedelta(days=7)
            data = web.DataReader(self.symbol, 'fred', start_date, datetime.now())
            if data.empty:
                logger.warning(f"No data for {self.symbol} received from FRED.")
                return False

            clean_data = data[self.symbol].dropna()
            for i in range(min(5, len(clean_data))):
                data_date = clean_data.index[-1 - i].date()
                value = clean_data.iloc[-1 - i]

                additional_data = json.dumps({"data_source": f"FRED ({self.symbol})"})
                self.repository.save_market_data(
                    indicator_type=self.indicator_type,
                    data_date=data_date,
                    value=value,
                    additional_data=additional_data
                )
            logger.info(f"Successfully updated {self.indicator_type.value} from FRED.")
            return True
        except Exception as e:
            logger.error(f"Error updating {self.indicator_type.value} from FRED: {e}", exc_info=True)
            return False
