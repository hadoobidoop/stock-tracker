# domain/market_data_backfiller/providers/put_call_ratio_provider.py
import json
from datetime import date, timedelta
import requests
import time

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PutCallRatioBackfillProvider(BaseBackfillProvider):
    """CBOE Put/Call 비율의 과거 데이터를 백필합니다."""

    def __init__(self, indicator_type: MarketIndicatorType):
        super().__init__()
        self.indicator_type = indicator_type

    def backfill(self, start_date: date, end_date: date) -> bool:
        logger.info(f"Backfilling Put/Call Ratio from CBOE for {start_date} to {end_date}...")
        
        current_date = start_date
        saved_count = 0
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            logger.debug(f"Fetching Put/Call ratio for {date_str}...")
            
            # DB에 데이터가 이미 있는지 확인
            if self.repository.get_market_data_by_date(self.indicator_type, current_date):
                logger.debug(f"Data for {date_str} already exists. Skipping.")
                current_date += timedelta(days=1)
                continue

            api_url = f"https://cdn.cboe.com/data/us/options/market_statistics/daily/{date_str}_daily_options"
            headers = {'User-Agent': 'Mozilla/5.0'}

            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'ratios' in data:
                        all_ratios = {item.get('name'): float(item.get('value')) for item in data['ratios'] if item.get('value')}
                        total_ratio = all_ratios.get('TOTAL PUT/CALL RATIO')

                        if total_ratio:
                            additional_data = json.dumps({"data_source": f"CBOE JSON API ({api_url})", "all_ratios": all_ratios})
                            success = self.repository.save_market_data(
                                indicator_type=self.indicator_type,
                                data_date=current_date,
                                value=total_ratio,
                                additional_data=additional_data
                            )
                            if success:
                                saved_count += 1
            except requests.RequestException:
                # 주말, 휴일 등 데이터가 없는 날은 404를 반환하므로 정상적인 실패로 간주하고 넘어감
                logger.debug(f"No data for {date_str} (likely a non-trading day).")
            except Exception as e:
                logger.warning(f"An error occurred while fetching data for {date_str}: {e}")
            
            current_date += timedelta(days=1)
            time.sleep(0.2)  # API 호출 제한 방지를 위한 짧은 지연

        logger.info(f"Successfully saved {saved_count} data points for Put/Call Ratio.")
        return True
