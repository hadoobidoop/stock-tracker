import json
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import pandas_datareader.data as web
import yfinance as yf

from domain.stock.service.indicator_providers.base_provider import BaseIndicatorProvider
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BuffettIndicatorProvider(BaseIndicatorProvider):
    """
    버핏 지수를 계산하고 업데이트하는 책임을 가집니다.
    Lookahead Bias를 제거하고, 일별 데이터를 생성하며, 증분 업데이트를 지원합니다.
    """

    def __init__(self, fred_preferred: bool = True, yahoo_helper: 'YahooApiHelper' = None):
        super().__init__()
        self.fred_preferred = fred_preferred
        self.yahoo_helper = yahoo_helper or YahooApiHelper()

    def update(self) -> bool:
        """하이브리드 방식으로 버핏 지수를 업데이트합니다."""
        logger.info("Starting Buffett Indicator update (Hybrid Mode)...")
        
        # 1. FRED 공식 데이터로 과거 데이터 재구성 및 업데이트
        fred_success = self._update_historical_with_fed_data()
        
        # 2. Yahoo Finance 데이터로 최신 데이터 추정 및 업데이트
        yahoo_success = self._update_recent_with_yahoo_data()

        if fred_success or yahoo_success:
            logger.info("Buffett Indicator update process completed.")
            return True
        else:
            logger.error("Both FRED and Yahoo methods failed for Buffett Indicator.")
            return False

    def _update_historical_with_fed_data(self) -> bool:
        """
        FRED 데이터를 사용하여 역사적 일별 버핏 지수를 생성하고 증분 업데이트합니다.
        Lookahead Bias를 방지하기 위해 시점(point-in-time)을 정확히 맞춥니다.
        """
        try:
            logger.info("Fetching historical data from FRED...")
            # 데이터 조회 기간 최적화: 최근 2년치 데이터만 가져와 처리
            start_date = datetime.now() - timedelta(days=365 * 2)
            end_date = datetime.now()

            # 1. 데이터 수집
            gdp_quarterly = web.DataReader('GDP', 'fred', start_date, end_date)
            market_cap_quarterly = web.DataReader('NCBEILQ027S', 'fred', start_date, end_date)

            if gdp_quarterly.empty or market_cap_quarterly.empty:
                logger.warning("Could not retrieve historical GDP or Market Cap data from FRED.")
                return False

            # 2. 데이터 전처리 및 일별 데이터 생성 (Forward-Fill)
            gdp = gdp_quarterly['GDP'].resample('D').ffill().dropna()
            market_cap = (market_cap_quarterly['NCBEILQ027S'] / 1000).resample('D').ffill().dropna() # 십억 달러로 변환

            # 3. 시점(Point-in-Time)에 맞게 데이터 병합
            df = pd.merge_asof(market_cap, gdp, left_index=True, right_index=True, direction='backward')
            df.columns = ['market_cap_billions', 'gdp_billions']
            df.dropna(inplace=True)

            # 4. 버핏 지수 계산
            df['buffett_ratio'] = (df['market_cap_billions'] / df['gdp_billions']) * 100

            # 5. 증분 업데이트 (DB에 없는 최신 데이터만 저장)
            latest_db_date = self.repository.get_latest_indicator_date(MarketIndicatorType.BUFFETT_INDICATOR)
            
            if latest_db_date:
                df_to_save = df[df.index.date > latest_db_date]
            else:
                df_to_save = df

            if df_to_save.empty:
                logger.info("No new historical Buffett Indicator data to save.")
                return True

            # 6. Bulk 저장을 위한 데이터 준비
            logger.info(f"Preparing {len(df_to_save)} historical Buffett Indicator records for batch save...")
            records_to_save = []
            for index, row in df_to_save.iterrows():
                records_to_save.append({
                    "indicator_type": MarketIndicatorType.BUFFETT_INDICATOR,
                    "date": index.date(),
                    "value": row['buffett_ratio'],
                    "additional_data": json.dumps({
                        "market_cap_billions": row['market_cap_billions'],
                        "gdp_billions": row['gdp_billions'],
                        "calculation_method": "fed_z1_market_cap_to_gdp_point_in_time",
                        "data_source": "Federal Reserve Z.1 (NCBEILQ027S) + FRED (GDP)"
                    })
                })
            
            # 7. 단일 트랜잭션으로 배치 저장
            with self.repository.transaction() as session:
                self.repository.save_market_data_batch(records_to_save, session)
            
            return True
        except Exception as e:
            logger.error(f"Error updating historical Buffett Indicator with Fed data: {e}", exc_info=True)
            return False

    def _update_recent_with_yahoo_data(self) -> bool:
        """
        Yahoo Finance 데이터를 사용하여 FRED 데이터가 없는 최신 기간의 버핏 지수를 추정합니다.
        """
        try:
            logger.info("Fetching recent data from Yahoo Finance for estimation...")
            # 1. 가장 최신의 GDP 데이터 가져오기
            gdp_start_date = datetime.now() - timedelta(days=365 * 2)
            gdp_data = web.DataReader('GDP', 'fred', gdp_start_date, datetime.now())
            if gdp_data.empty:
                logger.warning("Cannot fetch latest GDP for Yahoo-based estimation.")
                return False
            latest_gdp = gdp_data['GDP'].dropna().iloc[-1]

            # 2. Wilshire 5000 데이터 가져오기 (최근 3개월)
            wilshire_data = self.yahoo_helper.fetch_data_with_retry("^W5000", period="3mo")
            if wilshire_data is None or wilshire_data.empty:
                logger.error("Failed to fetch Wilshire 5000 data from Yahoo Finance.")
                return False

            # 3. 증분 업데이트 (DB에 없는 최신 데이터만 필터링)
            latest_db_date = self.repository.get_latest_indicator_date(MarketIndicatorType.BUFFETT_INDICATOR)
            if latest_db_date:
                wilshire_to_save = wilshire_data[wilshire_data.index.date > latest_db_date]
            else:
                wilshire_to_save = wilshire_data
            
            if wilshire_to_save.empty:
                logger.info("No new recent Buffett Indicator data to estimate and save.")
                return True

            # 4. Bulk 저장을 위한 데이터 준비
            logger.info(f"Estimating and preparing {len(wilshire_to_save)} recent Buffett Indicator records for batch save...")
            conversion_factor = 1.08
            records_to_save = []
            for date_idx, row in wilshire_to_save.iterrows():
                estimated_market_cap = row['Close'] * conversion_factor
                buffett_ratio = (estimated_market_cap / latest_gdp) * 100
                records_to_save.append({
                    "indicator_type": MarketIndicatorType.BUFFETT_INDICATOR,
                    "date": date_idx.date(),
                    "value": buffett_ratio,
                    "additional_data": json.dumps({
                        "wilshire_5000_points": float(row['Close']),
                        "market_cap_billions": float(estimated_market_cap),
                        "gdp_billions": float(latest_gdp),
                        "calculation_method": "yahoo_w5000_to_gdp_estimation",
                        "data_source": "Yahoo Finance (^W5000) + FRED (GDP)"
                    })
                })

            # 5. 단일 트랜잭션으로 배치 저장
            with self.repository.transaction() as session:
                self.repository.save_market_data_batch(records_to_save, session)

            return True
        except Exception as e:
            logger.error(f"Error updating recent Buffett Indicator with Yahoo data: {e}", exc_info=True)
            return False


# Yahoo API 호출 로직을 재사용 가능하도록 별도 헬퍼 클래스로 분리
class YahooApiHelper:
    def __init__(self, single_delay: float = 2.0, batch_delay: float = 2.0, retry_count: int = 3):
        self.single_delay = single_delay
        self.batch_delay = batch_delay
        self.retry_count = retry_count
        self.is_batch_mode = False

    def set_batch_mode(self, is_batch: bool):
        self.is_batch_mode = is_batch

    def fetch_data_with_retry(self, symbol: str, period: str = "5d") -> Optional[pd.DataFrame]:
        import time
        import random
        for attempt in range(self.retry_count):
            try:
                delay = (self.batch_delay if self.is_batch_mode else self.single_delay) + random.uniform(-0.5, 0.5)
                time.sleep(delay)
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)
                if not data.empty:
                    logger.info(f"Successfully fetched Yahoo data for {symbol} (attempt {attempt + 1})")
                    return data
            except Exception as e:
                logger.warning(f"Yahoo API error for {symbol} (attempt {attempt + 1}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to fetch Yahoo data for {symbol} after {self.retry_count} attempts.")
        return None
