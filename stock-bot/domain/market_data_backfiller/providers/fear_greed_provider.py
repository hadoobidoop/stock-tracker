# domain/market_data_backfiller/providers/fear_greed_provider.py
import json
from datetime import date, datetime, timedelta
import requests
from typing import List, Dict, Any

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.market_data import MarketData
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class FearGreedBackfillProvider(BaseBackfillProvider):
    """CNN 공포탐욕지수 API에서 모든 관련 지표 데이터를 가져와 파싱하는 책임을 가집니다."""

    def __init__(self):
        super().__init__()
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

    def backfill(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        CNN API에서 전체 데이터를 가져와, 지정된 기간에 맞는 레코드 딕셔너리 리스트를 반환합니다.
        DB 저장 로직은 오케스트레이터(Backfiller)가 담당합니다.
        """
        logger.info(f"Fetching Fear & Greed Index data from CNN for {start_date} to {end_date}...")
        
        api_url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://edition.cnn.com',
            'Referer': 'https://edition.cnn.com/',
        }
        
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        api_data = response.json()
        
        # --- 디버깅 로그 (INFO 레벨로 변경) ---
        logger.info(f"CNN API Response (first 500 chars): {json.dumps(api_data, indent=2)[:500]}")
        
        all_records = []
        for api_key, indicator_type in self.indicator_map.items():
            historical_data = api_data.get(api_key, {}).get('data', [])
            if not historical_data:
                logger.warning(f"No historical data for '{api_key}' in CNN API response.")
                continue

            for item in historical_data:
                # 타임존 문제를 피하기 위해 UTC 기준으로 날짜 변환
                data_date = datetime.utcfromtimestamp(int(float(item['x'])) / 1000).date()
                value = float(item['y'])
                
                if start_date <= data_date <= end_date:
                    all_records.append({
                        "indicator_type": indicator_type.value,
                        "date": data_date,
                        "value": value,
                        "additional_data": json.dumps({"data_source": "CNN Fear & Greed API (Historical)", "rating": item.get('rating')})
                    })
        
        logger.info(f"Successfully parsed {len(all_records)} records from CNN API.")
        return all_records

