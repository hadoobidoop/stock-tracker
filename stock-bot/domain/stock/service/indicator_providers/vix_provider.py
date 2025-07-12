import json
from datetime import datetime, timedelta

import pandas_datareader.data as web

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from domain.stock.service.indicator_providers.buffett_provider import YahooApiHelper
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VixProvider(BaseIndicatorProvider):
    """
    VIX 지수를 업데이트하는 책임을 가집니다.
    FRED 데이터를 우선 사용하고, 실패 시 Yahoo Finance로 대체합니다.
    """

    def __init__(self, fred_preferred: bool = True, yahoo_helper: 'YahooApiHelper' = None):
        super().__init__()
        self.fred_preferred = fred_preferred
        self.yahoo_helper = yahoo_helper or YahooApiHelper()

    def update(self) -> bool:
        logger.info("Starting VIX update...")
        if self.fred_preferred and self._update_with_fred():
            logger.info("VIX updated successfully using FRED data.")
            return True

        logger.info("Attempting VIX update using Yahoo Finance...")
        return self._update_with_yahoo()

    def _update_with_fred(self) -> bool:
        try:
            start_date = datetime.now() - timedelta(days=7)
            vix_data = web.DataReader('VIXCLS', 'fred', start_date, datetime.now())
            if vix_data.empty:
                logger.warning("No VIX data received from FRED.")
                return False

            vix_clean = vix_data['VIXCLS'].dropna()
            for i in range(min(5, len(vix_clean))):
                vix_date = vix_clean.index[-1 - i].date()
                vix_value = vix_clean.iloc[-1 - i]
                additional_data = json.dumps({"data_source": "FRED (VIXCLS)"})
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )
            return True
        except Exception as e:
            logger.error(f"Error updating VIX with FRED: {e}", exc_info=True)
            return False

    def _update_with_yahoo(self) -> bool:
        try:
            vix_data = self.yahoo_helper.fetch_data_with_retry("^VIX", period="5d")
            if vix_data is None or vix_data.empty:
                logger.error("Failed to fetch VIX data from Yahoo Finance.")
                return False

            recent_data = vix_data.tail(5)
            for date_idx, row in recent_data.iterrows():
                vix_date = date_idx.date()
                vix_value = row['Close']
                additional_data = json.dumps({"data_source": "Yahoo Finance (^VIX)"})
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )
            return True
        except Exception as e:
            logger.error(f"Error updating VIX with Yahoo: {e}", exc_info=True)
            return False
