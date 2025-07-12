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
        today = datetime.now().date()
        for days_back in range(5):
            target_date = today - timedelta(days=days_back)
            api_url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{target_date.strftime('%Y-%m-%d')}"
            headers = {'User-Agent': 'Mozilla/5.0'}

            try:
                response = requests.get(api_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    historical_data = data.get('fear_and_greed_historical', {}).get('data', [])
                    if historical_data:
                        latest_data = historical_data[-1]
                        data_date = datetime.fromtimestamp(int(float(latest_data['x'])) / 1000).date()
                        fear_greed_value = float(latest_data['y'])

                        if 0 <= fear_greed_value <= 100:
                            additional_data = json.dumps({"data_source": f"CNN Fear & Greed API ({api_url})"})
                            self.repository.save_market_data(
                                indicator_type=MarketIndicatorType.FEAR_GREED_INDEX,
                                data_date=data_date,
                                value=fear_greed_value,
                                additional_data=additional_data
                            )
                            logger.info(f"Saved CNN Fear & Greed Index for {data_date}: {fear_greed_value}")
                            return True
            except requests.RequestException as e:
                logger.warning(f"Request failed for CNN Fear & Greed API ({target_date}): {e}")
                continue
        return False

    def _update_with_vix_estimation(self) -> bool:
        try:
            # 최신 VIX 값을 DB에서 직접 조회
            latest_vix_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
            if latest_vix_data and latest_vix_data.value:
                vix_value = latest_vix_data.value
                estimated_fg = max(0, min(100, 100 - (vix_value - 10) * 3))
                additional_data = json.dumps({
                    "data_source": "VIX-based estimation",
                    "vix_value": vix_value,
                    "estimation_formula": "100 - (VIX - 10) * 3"
                })
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.FEAR_GREED_INDEX,
                    data_date=datetime.now().date(),
                    value=estimated_fg,
                    additional_data=additional_data
                )
                logger.info(f"Saved estimated Fear & Greed Index: {estimated_fg:.1f} (VIX-based)")
                return True
        except Exception as e:
            logger.error(f"Failed to create VIX-based Fear & Greed estimate: {e}")
        return False
