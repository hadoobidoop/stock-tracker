# domain/market_data_backfiller/providers/put_call_ratio_provider.py
import json
from datetime import date, timedelta
import requests
import time
from typing import List, Dict, Any

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class PutCallRatioBackfillProvider(BaseBackfillProvider):
    """CBOE Put/Call 비율의 과거 데이터를 파싱합니다."""

    def __init__(self):
        super().__init__()
        self.indicator_type = MarketIndicatorType.PUT_CALL_RATIO

    def backfill(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        logger.info(f"Fetching Put/Call Ratio from CBOE for {start_date} to {end_date}...")
        
        dates_to_fetch = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        
        records = []
        for target_date in dates_to_fetch:
            date_str = target_date.strftime('%Y-%m-%d')
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
                            logger.info(f"Successfully parsed Put/Call Ratio for {target_date}: {total_ratio}")
                            records.append({
                                "indicator_type": self.indicator_type,
                                "date": target_date,
                                "value": total_ratio,
                                "additional_data": json.dumps({"data_source": f"CBOE JSON API ({api_url})", "all_ratios": all_ratios})
                            })
            except requests.RequestException:
                logger.debug(f"No data for {date_str} (likely a non-trading day).")
            except Exception as e:
                logger.warning(f"An error occurred while fetching data for {date_str}: {e}")
            
            time.sleep(0.2)

        logger.info(f"Successfully parsed {len(records)} data points for Put/Call Ratio.")
        return records
