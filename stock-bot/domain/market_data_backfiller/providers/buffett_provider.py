# domain/market_data_backfiller/providers/buffett_provider.py
import json
from datetime import date, datetime
from typing import List, Dict, Any

import pandas as pd
import pandas_datareader.data as web

from .base_provider import BaseBackfillProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BuffettBackfillProvider(BaseBackfillProvider):
    """FRED 데이터를 사용하여 지정된 기간의 버핏 지수를 계산하고 반환합니다."""

    def __init__(self):
        super().__init__()
        self.indicator_type = MarketIndicatorType.BUFFETT_INDICATOR

    def backfill(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        지정된 기간 동안의 버핏 지수 데이터를 계산하여 딕셔너리 리스트로 반환합니다.
        """
        logger.info(f"Fetching Buffett Indicator data from FRED for {start_date} to {end_date}...")
        
        try:
            # 1. 데이터 수집 (요청 기간보다 1년 더 이전부터 가져와서 정확한 ffill 보장)
            fetch_start_date = start_date - pd.DateOffset(years=1)
            gdp_quarterly = web.DataReader('GDP', 'fred', fetch_start_date, end_date)
            market_cap_quarterly = web.DataReader('NCBEILQ027S', 'fred', fetch_start_date, end_date)

            if gdp_quarterly.empty or market_cap_quarterly.empty:
                logger.warning("Could not retrieve historical GDP or Market Cap data from FRED.")
                return []

            # 2. 데이터 전처리 및 일별 데이터 생성 (Forward-Fill)
            gdp = gdp_quarterly['GDP'].resample('D').ffill().dropna()
            market_cap = (market_cap_quarterly['NCBEILQ027S'] / 1000).resample('D').ffill().dropna()

            # 3. 시점(Point-in-Time)에 맞게 데이터 병합
            df = pd.merge_asof(market_cap, gdp, left_index=True, right_index=True, direction='backward')
            df.columns = ['market_cap_billions', 'gdp_billions']
            df.dropna(inplace=True)

            # 4. 버핏 지수 계산
            df['buffett_ratio'] = (df['market_cap_billions'] / df['gdp_billions']) * 100
            
            # 5. 요청된 기간(start_date, end_date)으로 최종 필터링
            df_to_return = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

            if df_to_return.empty:
                logger.info("No Buffett Indicator data available for the specified date range.")
                return []

            # 6. 딕셔너리 리스트로 변환 (개선된 방식)
            df_to_return_dict = df_to_return.to_dict('index')

            records = [
                {
                    "indicator_type": self.indicator_type,
                    "date": date_index.date(),
                    "value": data['buffett_ratio'],
                    "additional_data": json.dumps({
                        "market_cap_billions": data['market_cap_billions'],
                        "gdp_billions": data['gdp_billions'],
                        "calculation_method": "fed_z1_market_cap_to_gdp_point_in_time",
                        "data_source": "Federal Reserve Z.1 (NCBEILQ027S) + FRED (GDP)"
                    })
                }
                for date_index, data in df_to_return_dict.items()
            ]
            
            logger.info(f"Successfully parsed {len(records)} data points for Buffett Indicator.")
            return records

        except Exception as e:
            logger.error(f"Error during Buffett Indicator backfill: {e}", exc_info=True)
            return []
