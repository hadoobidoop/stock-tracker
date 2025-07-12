# domain/market_data_backfiller/providers/fear_greed_provider.py
import json
from datetime import date, datetime
import requests

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FearGreedBackfillProvider(BaseBackfillProvider):
    """CNN 공포탐욕지수의 과거 데이터를 백필합니다."""

    def __init__(self, indicator_type: MarketIndicatorType):
        super().__init__()
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> bool:
        logger.info(f"Backfilling Fear & Greed Index from CNN for {start_date} to {end_date}...")
        try:
            # CNN API는 요청 날짜부터 가장 최신까지의 모든 과거 데이터를 반환합니다.
            api_url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date.strftime('%Y-%m-%d')}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(api_url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"CNN API returned status {response.status_code}")
                return False

            data = response.json()
            historical_data = data.get('fear_and_greed_historical', {}).get('data', [])
            if not historical_data:
                logger.warning("No historical data found in CNN API response.")
                return False

            saved_count = 0
            for item in historical_data:
                data_date = datetime.fromtimestamp(int(float(item['x'])) / 1000).date()
                if start_date <= data_date <= end_date:
                    value = float(item['y'])
                    additional_data = json.dumps({"data_source": "CNN Fear & Greed API (Historical)"})
                    success = self.repository.save_market_data(
                        indicator_type=self.indicator_type,
                        data_date=data_date,
                        value=value,
                        additional_data=additional_data
                    )
                    if success:
                        saved_count += 1
            
            logger.info(f"Successfully saved {saved_count} data points for Fear & Greed Index.")
            return True
        except Exception as e:
            logger.error(f"Failed to backfill Fear & Greed Index: {e}", exc_info=True)
            return False
