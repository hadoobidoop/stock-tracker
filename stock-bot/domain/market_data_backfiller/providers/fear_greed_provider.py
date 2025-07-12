# domain/market_data_backfiller/providers/fear_greed_provider.py
import json
from datetime import date, datetime
import requests

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FearGreedBackfillProvider(BaseBackfillProvider):
    """CNN 공포탐욕지수와 그 7대 구성요소의 과거 데이터를 모두 백필합니다."""

    def __init__(self, indicator_type: MarketIndicatorType):
        super().__init__()
        # 이 Provider는 여러 indicator_type을 처리하지만, 대표 타입을 설정합니다.
        self.indicator_type = indicator_type
        
        # API 응답 키와 DB Enum을 매핑합니다.
        self.indicator_map = {
            "fear_and_greed_historical": MarketIndicatorType.FEAR_GREED_INDEX,
            "junk_bond_demand": MarketIndicatorType.FEAR_GREED_JUNK_BOND_DEMAND,
            "market_momentum_sp500": MarketIndicatorType.FEAR_GREED_MARKET_MOMENTUM,
            "market_volatility_vix": MarketIndicatorType.FEAR_GREED_MARKET_VOLATILITY,
            "put_call_options": MarketIndicatorType.FEAR_GREED_PUT_CALL_OPTIONS,
            "safe_haven_demand": MarketIndicatorType.FEAR_GREED_SAFE_HAVEN_DEMAND,
            "stock_price_breadth": MarketIndicatorType.FEAR_GREED_STOCK_PRICE_BREADTH,
            "stock_price_strength": MarketIndicatorType.FEAR_GREED_STOCK_PRICE_STRENGTH,
        }

    def backfill(self, start_date: date, end_date: date) -> bool:
        logger.info(f"Backfilling Fear & Greed Index and its components from CNN for {start_date} to {end_date}...")
        try:
            api_url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date.strftime('%Y-%m-%d')}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(api_url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"CNN API returned status {response.status_code}")
                return False

            api_data = response.json()
            
            total_saved_count = 0
            # 각 지표(종합 + 하위 7개)에 대해 백필링 실행
            for api_key, indicator_type in self.indicator_map.items():
                historical_data = api_data.get(api_key, {}).get('data', [])
                if not historical_data:
                    logger.warning(f"No historical data for '{api_key}' in CNN API response.")
                    continue

                # DB에서 해당 지표의 기존 데이터 날짜들을 미리 조회 (성능 최적화)
                existing_dates = self.repository.get_existing_dates(indicator_type, start_date)
                
                saved_count_per_indicator = 0
                for item in historical_data:
                    data_date = datetime.fromtimestamp(int(float(item['x'])) / 1000).date()
                    
                    # 지정된 기간 내에 있고, DB에 없는 데이터만 저장
                    if start_date <= data_date <= end_date and data_date not in existing_dates:
                        value = float(item['y'])
                        rating = item.get('rating')
                        additional_data = json.dumps({"data_source": "CNN Fear & Greed API (Historical)", "rating": rating})
                        
                        success = self.repository.save_market_data(
                            indicator_type=indicator_type,
                            data_date=data_date,
                            value=value,
                            additional_data=additional_data
                        )
                        if success:
                            saved_count_per_indicator += 1
                
                if saved_count_per_indicator > 0:
                    logger.info(f"Saved {saved_count_per_indicator} data points for {indicator_type.value}.")
                    total_saved_count += saved_count_per_indicator

            logger.info(f"Successfully saved a total of {total_saved_count} data points for Fear & Greed and its components.")
            return True
        except Exception as e:
            logger.error(f"Failed to backfill Fear & Greed data: {e}", exc_info=True)
            return False
