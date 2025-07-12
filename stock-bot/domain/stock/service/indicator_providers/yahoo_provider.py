import json
from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from domain.stock.service.indicator_providers.buffett_provider import YahooApiHelper
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class YahooProvider(BaseIndicatorProvider):
    """
    Yahoo Finance에서 단일 심볼 데이터를 가져오는 책임을 가집니다.
    """

    def __init__(self, symbol: str, indicator_type: MarketIndicatorType, yahoo_helper: 'YahooApiHelper' = None):
        super().__init__()
        self.symbol = symbol
        self.indicator_type = indicator_type
        self.yahoo_helper = yahoo_helper or YahooApiHelper()

    def update(self) -> bool:
        logger.info(f"Starting {self.indicator_type.value} update from Yahoo Finance (symbol: {self.symbol})...")
        try:
            data = self.yahoo_helper.fetch_data_with_retry(self.symbol, period="5d")
            if data is None or data.empty:
                logger.error(f"Failed to fetch {self.symbol} data from Yahoo Finance.")
                return False

            recent_data = data.tail(5)
            for date_idx, row in recent_data.iterrows():
                data_date = date_idx.date()
                value = row['Close']
                additional_data = json.dumps({"data_source": f"Yahoo Finance ({self.symbol})"})
                self.repository.save_market_data(
                    indicator_type=self.indicator_type,
                    data_date=data_date,
                    value=value,
                    additional_data=additional_data
                )
            logger.info(f"Successfully updated {self.indicator_type.value} from Yahoo Finance.")
            return True
        except Exception as e:
            logger.error(f"Error updating {self.indicator_type.value} from Yahoo Finance: {e}", exc_info=True)
            return False
