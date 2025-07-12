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
    데이터 누락을 방지하고, VIX 기반 추정치의 정확성을 높였습니다.
    """
    # VIX 기반 추정 공식 상수화
    VIX_ESTIMATION_BASE = 0.6
    VIX_ESTIMATION_FACTOR = 0.015
    VIX_ESTIMATION_MIN = 0.4
    VIX_ESTIMATION_MAX = 1.5
    VIX_ESTIMATION_FORMULA = f"{VIX_ESTIMATION_BASE} + (VIX - 20) * {VIX_ESTIMATION_FACTOR}"

    def __init__(self, vix_provider: VixProvider = None):
        super().__init__()
        self.vix_provider = vix_provider or VixProvider()

    def update(self) -> bool:
        logger.info("Starting Put/Call Ratio update...")
        try:
            # CBOE API를 먼저 시도하여 최대한 많은 데이터를 채웁니다.
            api_updated = self._update_from_cboe_api()

            # API 호출에 실패했거나, 가장 최신 날짜의 데이터를 여전히 얻지 못했다면 VIX 추정치를 사용합니다.
            latest_data = self.repository.get_latest_market_data(MarketIndicatorType.PUT_CALL_RATIO)
            if not latest_data or latest_data.date < (datetime.now().date() - timedelta(days=1)):
                logger.warning("CBOE data might be outdated, attempting VIX-based estimation.")
                vix_estimation_updated = self._update_with_vix_estimation()
                return api_updated or vix_estimation_updated

            return api_updated

        except Exception as e:
            logger.error(f"Error updating Put/Call ratio: {e}", exc_info=True)
            return False

    def _update_from_cboe_api(self) -> bool:
        headers = {'User-Agent': 'Mozilla/5.0'}
        today = datetime.now().date()
        days_to_check = 5
        
        # 1. DB에서 이미 데이터가 있는 날짜 확인
        start_date = today - timedelta(days=days_to_check - 1)
        existing_dates = self.repository.get_existing_dates(MarketIndicatorType.PUT_CALL_RATIO, start_date)

        # 2. DB에 없는 날짜에 대해서만 API 호출
        dates_to_fetch = [today - timedelta(days=i) for i in range(days_to_check) if (today - timedelta(days=i)) not in existing_dates]

        if not dates_to_fetch:
            logger.info("Put/Call ratio data is up-to-date. No API call needed.")
            return True

        update_succeeded = False
        for target_date in dates_to_fetch:
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://cdn.cboe.com/data/us/options/market_statistics/daily/{date_str}_daily_options"

            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'ratios' in data:
                        all_ratios = {item.get('name'): float(item.get('value')) for item in data['ratios'] if item.get('value')}
                        total_ratio = all_ratios.get('TOTAL PUT/CALL RATIO')

                        if total_ratio:
                            additional_data = json.dumps({"data_source": f"CBOE JSON API ({api_url})", "all_ratios": all_ratios})
                            self.repository.save_market_data(
                                indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                                data_date=target_date,
                                value=total_ratio,
                                additional_data=additional_data
                            )
                            logger.info(f"Saved CBOE TOTAL PUT/CALL RATIO for {date_str}: {total_ratio:.3f}")
                            update_succeeded = True
            except requests.RequestException as e:
                logger.warning(f"Request failed for CBOE API {date_str}: {e}")
                continue
        
        return update_succeeded

    def _update_with_vix_estimation(self) -> bool:
        try:
            latest_vix_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
            if latest_vix_data and latest_vix_data.value:
                vix_value = latest_vix_data.value
                
                # 추정치의 날짜는 VIX 데이터의 날짜를 사용
                data_date_for_estimation = latest_vix_data.date

                # 해당 날짜에 이미 데이터가 있는지 최종 확인
                if self.repository.get_market_data_by_date(MarketIndicatorType.PUT_CALL_RATIO, data_date_for_estimation):
                    logger.info(f"Estimated Put/Call ratio for {data_date_for_estimation} is not needed as data already exists.")
                    return True

                estimated_pc_ratio = max(self.VIX_ESTIMATION_MIN, min(self.VIX_ESTIMATION_MAX, self.VIX_ESTIMATION_BASE + (vix_value - 20) * self.VIX_ESTIMATION_FACTOR))
                additional_data = json.dumps({
                    "data_source": "VIX-based estimation (CBOE API fallback)",
                    "vix_value": vix_value,
                    "estimation_formula": self.VIX_ESTIMATION_FORMULA
                })
                self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                    data_date=data_date_for_estimation,
                    value=estimated_pc_ratio,
                    additional_data=additional_data
                )
                logger.info(f"Saved estimated Put/Call Ratio for {data_date_for_estimation}: {estimated_pc_ratio:.3f} (VIX-based)")
                return True
        except Exception as e:
            logger.error(f"Failed to create VIX-based Put/Call estimate: {e}")
        return False

