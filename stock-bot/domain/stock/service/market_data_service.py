"""
시장 데이터 수집 및 관리 서비스 (오케스트레이터)
각 지표별 Provider를 총괄하여 데이터 수집을 조율합니다.
"""
import json
from datetime import date
from typing import Optional, Dict, List, Any

import pandas as pd

from domain.stock.service.indicator_providers import (
    BuffettIndicatorProvider, VixProvider, FearGreedIndexProvider,
    PutCallRatioProvider, FredProvider, YahooProvider, Sp500SmaProvider, YahooApiHelper
)
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """
    시장 데이터 오케스트레이션 서비스.
    각종 지표 Provider를 관리하고 데이터 수집 워크플로우를 실행합니다.
    """

    def __init__(self):
        self.repository = SQLMarketDataRepository()
        self.stock_repository = SQLStockRepository()

        # API 헬퍼 및 설정
        self.yahoo_helper = YahooApiHelper()
        self.fred_preferred = True

        # 각 지표별 Provider 등록
        self.buffett_provider = BuffettIndicatorProvider(self.fred_preferred, self.yahoo_helper)
        self.vix_provider = VixProvider(self.fred_preferred, self.yahoo_helper)
        self.fear_greed_provider = FearGreedIndexProvider(vix_provider=self.vix_provider)
        self.put_call_ratio_provider = PutCallRatioProvider(vix_provider=self.vix_provider)
        self.treasury_yield_provider = FredProvider('DGS10', MarketIndicatorType.US_10Y_TREASURY_YIELD)
        self.gold_provider = YahooProvider('GC=F', MarketIndicatorType.GOLD_PRICE, self.yahoo_helper)
        self.oil_provider = YahooProvider('CL=F', MarketIndicatorType.CRUDE_OIL_PRICE, self.yahoo_helper)
        self.sp500_provider = YahooProvider('^GSPC', MarketIndicatorType.SP500_INDEX, self.yahoo_helper)
        self.dxy_provider = YahooProvider('DX-Y.NYB', MarketIndicatorType.DXY, self.yahoo_helper)
        self.sp500_sma_provider = Sp500SmaProvider()

        self.providers = [
            self.buffett_provider,
            self.vix_provider,
            self.treasury_yield_provider,
            self.gold_provider,
            self.oil_provider,
            self.sp500_provider,
            self.put_call_ratio_provider,
            self.fear_greed_provider,
            self.dxy_provider,
            self.sp500_sma_provider,
        ]

    def update_all_indicators(self) -> None:
        """모든 지표를 업데이트합니다."""
        logger.info("Starting update of all market indicators (batch mode)...")
        self.yahoo_helper.set_batch_mode(True)
        results = {}
        try:
            for provider in self.providers:
                # S&P 500 SMA는 S&P 500 지수 업데이트 성공 시에만 실행
                if isinstance(provider, Sp500SmaProvider):
                    if results.get(self.sp500_provider.provider_name, False):
                        results[provider.provider_name] = provider.update()
                    else:
                        results[provider.provider_name] = False
                        logger.warning("Skipping S&P 500 SMA calculation due to index update failure.")
                else:
                    results[provider.provider_name] = provider.update()
            
            success_count = sum(results.values())
            logger.info(f"Market indicators update completed: {success_count}/{len(results)} successful")
            return results
        finally:
            self.yahoo_helper.set_batch_mode(False)

    # --- 데이터 조회 메서드 (외부 인터���이스 유지) ---

    def get_vix_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 VIX를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.VIX, target_date)
        return data.value if data else None

    def get_treasury_yield_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 10년 국채 수익률을 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.US_10Y_TREASURY_YIELD, target_date)
        return data.value if data else None

    def get_buffett_indicator_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 버핏 지수를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.BUFFETT_INDICATOR, target_date)
        return data.value if data else None

    def get_put_call_ratio_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 Put/Call 비율을 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.PUT_CALL_RATIO, target_date)
        return data.value if data else None

    def get_fear_greed_index_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 공포탐욕지수를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.FEAR_GREED_INDEX, target_date)
        return data.value if data else None

    def get_macro_data_for_date(self, target_date: date, required_indicators: List[str]) -> Dict[str, Any]:
        """특정 날짜와 요구되는 지표 목록을 기반으로, 모든 거시 경제 지표를 조회합니다."""
        macro_data = {}
        indicator_map = {
            'VIX': MarketIndicatorType.VIX,
            'US_10Y_TREASURY_YIELD': MarketIndicatorType.US_10Y_TREASURY_YIELD,
            'BUFFETT_INDICATOR': MarketIndicatorType.BUFFETT_INDICATOR,
            'PUT_CALL_RATIO': MarketIndicatorType.PUT_CALL_RATIO,
            'FEAR_GREED_INDEX': MarketIndicatorType.FEAR_GREED_INDEX,
            'DXY': MarketIndicatorType.DXY,
            'SP500_SMA_200': MarketIndicatorType.SP500_SMA_200,
            'SP500_INDEX': MarketIndicatorType.SP500_INDEX,
            'GOLD_PRICE': MarketIndicatorType.GOLD_PRICE,
            'CRUDE_OIL_PRICE': MarketIndicatorType.CRUDE_OIL_PRICE,
        }
        for indicator_name in required_indicators:
            indicator_type = indicator_map.get(indicator_name)
            if indicator_type:
                data = self.repository.get_market_data_by_date_with_forward_fill(indicator_type, target_date)
                macro_data[indicator_name] = data.value if data else None
            else:
                logger.warning(f"No fetch function defined for required indicator: {indicator_name}")
                macro_data[indicator_name] = None
        return macro_data

    def get_daily_ohlcv(self, ticker: str, end_date: date, limit: int = 200) -> Optional[pd.DataFrame]:
        """특정 종목의 일봉 OHLCV 데이터를 DB 우선으로 가져옵니다."""
        days_to_fetch = int(limit * 1.5)
        data_dict = self.stock_repository.fetch_and_cache_ohlcv([ticker], days=days_to_fetch, interval="1d")
        if ticker in data_dict and not data_dict[ticker].empty:
            df = data_dict[ticker]
            return df[df.index.date <= end_date].tail(limit)
        return None

    def get_hourly_ohlcv(self, ticker: str, end_date: date, limit: int = 100) -> Optional[pd.DataFrame]:
        """특정 종목의 시간봉 OHLCV 데이터를 DB 우선으로 가져옵니다."""
        days_to_fetch = min(729, int(limit / 8 * 1.5))
        data_dict = self.stock_repository.fetch_and_cache_ohlcv([ticker], days=days_to_fetch, interval="60m")
        if ticker in data_dict and not data_dict[ticker].empty:
            df = data_dict[ticker]
            return df[df.index.date <= end_date].tail(limit)
        return None

    def get_latest_buffett_indicator(self) -> Optional[float]:
        """최신 버핏 지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)
        return latest_data.value if latest_data else None

    def get_latest_vix(self) -> Optional[float]:
        """최신 VIX를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
        return latest_data.value if latest_data else None

    def get_latest_fear_greed_index(self) -> Optional[float]:
        """최신 공포탐욕지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.FEAR_GREED_INDEX)
        return latest_data.value if latest_data else None

    def get_latest_gold_price(self) -> Optional[float]:
        """최신 금 가격을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.GOLD_PRICE)
        return latest_data.value if latest_data else None

    def get_latest_crude_oil_price(self) -> Optional[float]:
        """최신 원유 가격을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.CRUDE_OIL_PRICE)
        return latest_data.value if latest_data else None

    def get_latest_sp500_index(self) -> Optional[float]:
        """최신 S&P 500 지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.SP500_INDEX)
        return latest_data.value if latest_data else None

    def get_latest_treasury_yield(self) -> Optional[float]:
        """최신 10년 국채 수익률을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.US_10Y_TREASURY_YIELD)
        return latest_data.value if latest_data else None

    def get_latest_put_call_ratio(self) -> Optional[float]:
        """최신 Put/Call 비율을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.PUT_CALL_RATIO)
        return latest_data.value if latest_data else None