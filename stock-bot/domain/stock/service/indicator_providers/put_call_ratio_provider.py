import json
from datetime import datetime, timedelta
import requests

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from domain.stock.service.indicator_providers.vix_provider import VixProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PutCallRatioProvider(BaseIndicatorProvider):
    """
    CBOE Put/Call 비율을 업데이트하는 책임을 가집니다.
    API 호출 실패 시 VIX 기반 추정치를 사용합니다.
    """

    def __init__(self, vix_provider: VixProvider = None):
        super().__init__()
        self.vix_provider = vix_provider or VixProvider()

    def update(self) -> bool:
        logger.info("Starting Put/Call Ratio update...")
        try:
            if self._update_from_cboe_api():
                return True

            logger.warning("CBOE API failed, using VIX-based estimation for Put/Call Ratio.")
            return self._update_with_vix_estimation()

        except Exception as e:
            logger.error(f"Error updating Put/Call ratio: {e}", exc_info=True)
            return False

    def _update_from_cboe_api(self) -> bool:
        headers = {'User-Agent': 'Mozilla/5.0'}
        for i in range(5):
            target_date = datetime.now().date() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://cdn.cboe.com/data/us/options/market_statistics/daily/{date_str}_daily_options"

            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'ratios' in data:
                        all_ratios = {item.get('name'): float(item.get('value')) for item in data['ratios'] if
                                      item.get('value')}
                        total_ratio = all_ratios.get('TOTAL PUT/CALL RATIO')

                        if total_ratio:
                            additional_data = json.dumps({
                                "data_source": f"CBOE JSON API ({api_url})",
                                "all_ratios": all_ratios
                            })
                            self.repository.save_market_data(
                                indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                                data_date=target_date,
                                value=total_ratio,
                                additional_data=additional_data
                            )
                            logger.info(f"Saved CBOE TOTAL PUT/CALL RATIO for {date_str}: {total_ratio:.3f}")
                            return True
            except requests.RequestException as e:
                logger.warning(f"Request failed for CBOE API {date_str}: {e}")
                continue
        return False

    def _update_with_vix_estimation(self) -> bool:
        try:
            latest_vix_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
            if latest_vix_data and latest_vix_data.value:
                vix_value = latest_vix_data.value
                estimated_pc_ratio = max(0.4, min(1.5, 0.6 + (vix_value - 20) * 0.015))
                additional_data = json.dumps({
                    "data_source": "VIX-based estimation (CBOE API fallback)",
                    "vix_value": vix_value,
                    "estimation_formula": "0.6 + (VIX - 20) * 0.015"
                })
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                    data_date=datetime.now().date(),
                    value=estimated_pc_ratio,
                    additional_data=additional_data
                )
                logger.info(f"Saved estimated Put/Call Ratio: {estimated_pc_ratio:.3f} (VIX-based)")
                return True
        except Exception as e:
            logger.error(f"Failed to create VIX-based Put/Call estimate: {e}")
        return False
