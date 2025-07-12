import json
from datetime import datetime, timedelta
import requests

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from domain.stock.service.indicator_providers.vix_provider import VixProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FearGreedIndexProvider(BaseIndicatorProvider):
    """
    CNN 공포탐욕지수를 업데이트하는 책임을 가집니다.
    API 호출 실패 시 VIX 기반 추정치를 사용합니다.
    """

    def __init__(self, vix_provider: VixProvider = None):
        super().__init__()
        self.vix_provider = vix_provider or VixProvider()

    def update(self) -> bool:
        logger.info("Starting Fear & Greed Index update...")
        try:
            if self._update_from_cnn_api():
                return True

            logger.warning("Failed to get Fear & Greed Index from CNN API, using VIX-based estimation.")
            return self._update_with_vix_estimation()

        except Exception as e:
            logger.error(f"Error updating Fear & Greed Index: {e}", exc_info=True)
            return False

    def _update_from_cnn_api(self) -> bool:
        api_url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://edition.cnn.com',
            'Referer': 'https://edition.cnn.com/',
        }

        try:
            logger.info(f"Fetching Fear & Greed Index from CNN API: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"CNN API returned status {response.status_code}")
                return False

            data = response.json()
            main_index_data = data.get('fear_and_greed')
            if not main_index_data or 'score' not in main_index_data:
                logger.warning("Main 'fear_and_greed' score not found in CNN API response.")
                return False

            # --- 최신 데이터 저장 ---
            fear_greed_value = float(main_index_data['score'])
            data_date = datetime.fromisoformat(main_index_data.get('timestamp').replace("Z", "+00:00")).date()

            if not self.repository.get_market_data_by_date(MarketIndicatorType.FEAR_GREED_INDEX, data_date):
                components = {k: {'score': v.get('score'), 'rating': v.get('rating')} for k, v in data.items() if isinstance(v, dict) and 'score' in v and k not in ['fear_and_greed', 'fear_and_greed_historical']}
                additional_data = json.dumps({"data_source": "CNN Fear & Greed API", "rating": main_index_data.get('rating'), "components": components})
                self.repository.save_market_data(MarketIndicatorType.FEAR_GREED_INDEX, data_date, fear_greed_value, additional_data)
                logger.info(f"Saved CNN Fear & Greed Index for {data_date}: {fear_greed_value}")

            # --- 누락된 과거 데이터 채우기(Backfill) 로직 ---
            logger.info("Checking for historical data to backfill...")
            historical_data = data.get('fear_and_greed_historical', {}).get('data', [])
            if historical_data:
                start_date = datetime.fromtimestamp(int(float(historical_data[0]['x'])) / 1000).date()
                existing_dates = self.repository.get_existing_dates(MarketIndicatorType.FEAR_GREED_INDEX, start_date)
                
                backfilled_count = 0
                for item in historical_data:
                    hist_date = datetime.fromtimestamp(int(float(item['x'])) / 1000).date()
                    if hist_date not in existing_dates:
                        hist_value = float(item['y'])
                        additional_data_hist = json.dumps({"data_source": "CNN Fear & Greed API (Historical)"})
                        self.repository.save_market_data(MarketIndicatorType.FEAR_GREED_INDEX, hist_date, hist_value, additional_data_hist)
                        backfilled_count += 1
                if backfilled_count > 0:
                    logger.info(f"Backfilled {backfilled_count} missing historical data points.")
            
            return True

        except requests.RequestException as e:
            logger.error(f"Request failed for CNN Fear & Greed API: {e}", exc_info=True)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse CNN API response: {e}", exc_info=True)
        
        return False

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
