import json
from datetime import datetime, timedelta, date
import requests
from typing import Dict

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from domain.stock.service.indicator_providers.vix_provider import VixProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FearGreedIndexProvider(BaseIndicatorProvider):
    """
    CNN 공포탐욕지수 및 모든 하위 지표의 최신 5일치 데이터를 업데이트합니다.
    API 호출 실패 시 VIX 기반 추정치를 사용합니다.
    """

    def __init__(self, vix_provider: VixProvider = None):
        super().__init__()
        self.vix_provider = vix_provider or VixProvider()
        self.indicator_map = {
            "fear_and_greed": MarketIndicatorType.FEAR_GREED_INDEX,
            "junk_bond_demand": MarketIndicatorType.FEAR_GREED_JUNK_BOND_DEMAND,
            "market_momentum_sp500": MarketIndicatorType.FEAR_GREED_MARKET_MOMENTUM,
            "market_volatility_vix": MarketIndicatorType.FEAR_GREED_MARKET_VOLATILITY,
            "put_call_options": MarketIndicatorType.FEAR_GREED_PUT_CALL_OPTIONS,
            "safe_haven_demand": MarketIndicatorType.FEAR_GREED_SAFE_HAVEN_DEMAND,
            "stock_price_breadth": MarketIndicatorType.FEAR_GREED_STOCK_PRICE_BREADTH,
            "stock_price_strength": MarketIndicatorType.FEAR_GREED_STOCK_PRICE_STRENGTH,
        }

    def update(self) -> bool:
        logger.info("Starting Fear & Greed Index and components update for the last 5 days...")
        try:
            # _update_from_cnn_api가 한 번이라도 성공하면 True를 반환
            if self._update_from_cnn_api():
                return True

            logger.warning("Failed to get any Fear & Greed data from CNN API for the last 5 days, using VIX-based estimation for the main index.")
            return self._update_with_vix_estimation()

        except Exception as e:
            logger.error(f"Error updating Fear & Greed Index: {e}", exc_info=True)
            return False

    def _update_from_cnn_api(self) -> bool:
        today = date.today()
        successful_update_found = False

        for i in range(5):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{date_str}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://edition.cnn.com',
                'Referer': 'https://edition.cnn.com/',
            }

            try:
                logger.info(f"Fetching Fear & Greed data for {date_str} from: {api_url}")
                response = requests.get(api_url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    logger.info(f"No data for {date_str} (status code: {response.status_code}). Likely a non-trading day. Skipping.")
                    continue

                data = response.json()
                
                # 응답의 타임스탬프를 우선하여 정확한 날짜를 사용
                timestamp_str = data.get('fear_and_greed', {}).get('timestamp')
                if timestamp_str:
                    actual_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).date()
                else:
                    actual_date = target_date  # 타임스탬프가 없으면 순회 날짜를 사용

                # 데이터가 성공적으로 수신되었음을 표시
                successful_update_found = True
                
                for api_key, indicator_type in self.indicator_map.items():
                    indicator_data = data.get(api_key)
                    
                    if not indicator_data or 'score' not in indicator_data:
                        logger.warning(f"Indicator '{api_key}' not found in response for {date_str}.")
                        continue
                        
                    value = float(indicator_data['score'])
                    rating = indicator_data.get('rating', 'N/A')
                    
                    additional_data = json.dumps({
                        "data_source": "CNN Fear & Greed API (Daily)",
                        "rating": rating
                    })
                    
                    # repository.save_market_data가 upsert를 처리
                    self.repository.save_market_data(indicator_type, actual_date, value, additional_data)
                    logger.info(f"Upserted {indicator_type.value} for {actual_date}: {value:.2f}")

            except requests.RequestException as e:
                logger.error(f"Request failed for {date_str}: {e}", exc_info=True)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse response for {date_str}: {e}", exc_info=True)
        
        return successful_update_found

    def _update_with_vix_estimation(self) -> bool:
        try:
            latest_vix_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
            if latest_vix_data and latest_vix_data.value:
                vix_value = latest_vix_data.value
                
                # VIX 데이터의 날짜를 사용
                data_date_for_estimation = latest_vix_data.date
                
                # 추정치를 저장하기 전에 해당 날짜에 실제 데이터가 있는지 최종 확인
                if self.repository.get_market_data_by_date(MarketIndicatorType.FEAR_GREED_INDEX, data_date_for_estimation):
                    logger.info(f"Estimated F&G index for {data_date_for_estimation} is not needed as data already exists.")
                    return True

                estimated_fg = max(0, min(100, 100 - (vix_value - 10) * 3))
                additional_data = json.dumps({
                    "data_source": "VIX-based estimation",
                    "vix_value": vix_value,
                    "estimation_formula": "100 - (VIX - 10) * 3"
                })
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.FEAR_GREED_INDEX,
                    data_date=data_date_for_estimation,
                    value=estimated_fg,
                    additional_data=additional_data
                )
                logger.info(f"Saved estimated Fear & Greed Index for {data_date_for_estimation}: {estimated_fg:.1f} (VIX-based)")
                return True
        except Exception as e:
            logger.error(f"Failed to create VIX-based Fear & Greed estimate: {e}")
        return False
