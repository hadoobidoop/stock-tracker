"""
시장 데이터 수집 및 관리 서비스
버핏 지수, VIX, 공포지수 등 다양한 시장 지표를 수집합니다.
"""
import pandas_datareader.data as web
import yfinance as yf
import requests
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple
import json
import time
import random

from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """시장 데이터 수집 및 관리 서비스"""

    def __init__(self):
        self.repository = SQLMarketDataRepository()
        # API 호출 제한 방지를 위한 설정
        self.yahoo_request_delay = 1.0  # Yahoo API 호출 간 최소 지연 시간 (초)
        self.yahoo_retry_count = 3  # Yahoo API 재시도 횟수
        self.fred_preferred = True  # FRED를 우선 사용

    def _delay_for_yahoo_api(self):
        """Yahoo API 호출 제한을 피하기 위한 지연"""
        # 0.8 ~ 1.2초 사이의 랜덤한 지연
        delay = self.yahoo_request_delay + random.uniform(-0.2, 0.2)
        time.sleep(delay)

    def _fetch_yahoo_data_with_retry(self, symbol: str, period: str = "5d") -> Optional[Any]:
        """
        Yahoo Finance에서 데이터를 가져오되 재시도 로직 포함
        
        Args:
            symbol: Yahoo Finance 심볼
            period: 데이터 기간 ("5d", "1mo", "3mo" 등)
            
        Returns:
            Yahoo Finance 데이터 또는 None
        """
        for attempt in range(self.yahoo_retry_count):
            try:
                self._delay_for_yahoo_api()
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)
                
                if not data.empty:
                    logger.info(f"Successfully fetched Yahoo data for {symbol} (attempt {attempt + 1})")
                    return data
                else:
                    logger.warning(f"Empty data from Yahoo for {symbol} (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.warning(f"Yahoo API error for {symbol} (attempt {attempt + 1}): {e}")
                
                if attempt < self.yahoo_retry_count - 1:
                    # 재시도 전 추가 지연
                    time.sleep(2 ** attempt)  # 지수적 백오프
                    
        logger.error(f"Failed to fetch Yahoo data for {symbol} after {self.yahoo_retry_count} attempts")
        return None

    def update_buffett_indicator(self) -> bool:
        """
        Federal Reserve Z.1 Financial Accounts 데이터를 우선 사용하고,
        실패 시 Yahoo Finance ^W5000을 백업으로 사용하여 버핏 지수를 계산합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Buffett Indicator update...")
        
        # 1. Fed Z.1 데이터로 시도 (기본 방식)
        if self.fred_preferred and self._update_buffett_with_fed_data():
            logger.info("Buffett Indicator updated successfully using Fed Z.1 data")
            return True
            
        # 2. Yahoo Finance ^W5000으로 백업 시도
        logger.info("Attempting Buffett Indicator update using Yahoo Finance ^W5000...")
        return self._update_buffett_with_yahoo_data()

    def _update_buffett_with_fed_data(self) -> bool:
        """Fed Z.1 데이터를 사용한 버핏 지수 업데이트 (기존 로직)"""
        try:
            # GDP 데이터 가져오기 (FRED)
            start_date = datetime.now() - timedelta(days=365)  # 1년 범위
            end_date = datetime.now()
            
            gdp = web.DataReader('GDP', 'fred', start_date, end_date)
            
            if gdp.empty:
                logger.warning("No GDP data received from FRED")
                return False
                
            gdp_clean = gdp['GDP'].dropna()
            if gdp_clean.empty:
                logger.warning("No valid GDP data available")
                return False
                
            latest_gdp = gdp_clean.iloc[-1]  # billion USD
            logger.info(f"Latest GDP: ${latest_gdp:.2f} billion USD")
            
            # Federal Reserve Z.1 Financial Accounts 데이터 가져오기
            market_data = web.DataReader('NCBEILQ027S', 'fred', start_date, end_date)
            
            if market_data.empty:
                logger.warning("No market cap data received from Fed Z.1")
                return False
                
            market_clean = market_data['NCBEILQ027S'].dropna()
            if market_clean.empty:
                logger.warning("No valid market cap data available")
                return False
                
            # Fed Z.1 데이터는 백만 달러 단위이므로 십억 달러로 변환
            latest_market_cap_millions = market_clean.iloc[-1]
            latest_market_cap_billions = latest_market_cap_millions / 1000
            
            logger.info(f"Latest Market Cap: ${latest_market_cap_billions:.1f} billion USD")
            
            # 최근 5일간의 데이터로 버핏 지수 계산
            for i in range(min(5, len(market_clean))):
                market_date = market_clean.index[-1-i].date()
                market_cap_millions = market_clean.iloc[-1-i]
                market_cap_billions = market_cap_millions / 1000  # 백만 달러 → 십억 달러
                
                buffett_ratio = (market_cap_billions / latest_gdp) * 100
                
                additional_data = json.dumps({
                    "market_cap_billions": float(market_cap_billions),
                    "market_cap_trillions": float(market_cap_billions / 1000),
                    "gdp_billions": float(latest_gdp),
                    "gdp_trillions": float(latest_gdp / 1000),
                    "calculation_method": "fed_z1_market_cap_to_gdp",
                    "data_source": "Federal Reserve Z.1 (NCBEILQ027S) + FRED (GDP)",
                    "note": "Fed Z.1: Nonfinancial corporate business; corporate equities; liability, Level"
                })
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.BUFFETT_INDICATOR,
                    data_date=market_date,
                    value=buffett_ratio,
                    additional_data=additional_data
                )
                
                if success:
                    logger.info(f"Saved Buffett Indicator for {market_date}: {buffett_ratio:.1f}%")

            return True

        except Exception as e:
            logger.error(f"Error updating Buffett Indicator with Fed data: {e}", exc_info=True)
            return False

    def _update_buffett_with_yahoo_data(self) -> bool:
        """Yahoo Finance ^W5000 데이터를 사용한 버핏 지수 업데이트 (백업 방식)"""
        try:
            # 1. GDP 데이터 (FRED에서 여전히 가져오기)
            start_date = datetime.now() - timedelta(days=365)
            gdp = web.DataReader('GDP', 'fred', start_date, datetime.now())
            
            if gdp.empty:
                logger.warning("No GDP data for Yahoo-based Buffett calculation")
                return False
                
            gdp_clean = gdp['GDP'].dropna()
            latest_gdp = gdp_clean.iloc[-1]  # billion USD
            logger.info(f"GDP for Yahoo calculation: ${latest_gdp:.2f} billion USD")
            
            # 2. Yahoo Finance ^W5000 데이터 가져오기 (API 호출 제한 고려)
            wilshire_data = self._fetch_yahoo_data_with_retry("^W5000", period="1mo")
            
            if wilshire_data is None or wilshire_data.empty:
                logger.error("Failed to fetch Wilshire 5000 data from Yahoo Finance")
                return False
                
            # 3. Wilshire 5000 포인트를 시가총액으로 변환
            # 일반적으로 1 포인트 ≈ 1.05-1.1 billion USD (2024년 기준)
            conversion_factor = 1.08  # 보수적 추정치
            
            # 최근 5일간의 데이터 처리 (API 호출 최소화)
            recent_data = wilshire_data.tail(5)
            
            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                market_date = date_idx.date()
                wilshire_value = row['Close']
                
                # 시가총액 계산 (billion USD)
                estimated_market_cap = wilshire_value * conversion_factor
                
                # 버핏 지수 계산
                buffett_ratio = (estimated_market_cap / latest_gdp) * 100
                
                additional_data = json.dumps({
                    "wilshire_5000_points": float(wilshire_value),
                    "conversion_factor": conversion_factor,
                    "market_cap_billions": float(estimated_market_cap),
                    "market_cap_trillions": float(estimated_market_cap / 1000),
                    "gdp_billions": float(latest_gdp),
                    "gdp_trillions": float(latest_gdp / 1000),
                    "calculation_method": "yahoo_w5000_to_gdp",
                    "data_source": "Yahoo Finance (^W5000) + FRED (GDP)",
                    "note": f"Wilshire 5000 converted using factor {conversion_factor}x"
                })
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.BUFFETT_INDICATOR,
                    data_date=market_date,
                    value=buffett_ratio,
                    additional_data=additional_data
                )
                
                if success:
                    logger.info(f"Saved Yahoo-based Buffett Indicator for {market_date}: {buffett_ratio:.1f}% "
                              f"(Wilshire: {wilshire_value:.0f} pts, Market Cap: ${estimated_market_cap:.1f}B)")

            return True

        except Exception as e:
            logger.error(f"Error updating Buffett Indicator with Yahoo data: {e}", exc_info=True)
            return False

    def update_vix(self) -> bool:
        """
        FRED에서 VIX 데이터를 우선 가져오고, 실패 시 Yahoo Finance에서 백업으로 가져옵니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting VIX update...")
        
        # 1. FRED에서 VIX 데이터 시도 (기본 방식)
        if self.fred_preferred and self._update_vix_with_fred():
            logger.info("VIX updated successfully using FRED data")
            return True
            
        # 2. Yahoo Finance에서 VIX 백업 시도
        logger.info("Attempting VIX update using Yahoo Finance...")
        return self._update_vix_with_yahoo()

    def _update_vix_with_fred(self) -> bool:
        """FRED에서 VIX 데이터 업데이트 (기존 로직)"""
        try:
            # 최근 7일간의 데이터 가져오기
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            # FRED에서 VIX 데이터 가져오기
            vix_data = web.DataReader('VIXCLS', 'fred', start_date, end_date)
            
            if vix_data.empty:
                logger.warning("No VIX data received from FRED")
                return False

            vix_clean = vix_data['VIXCLS'].dropna()
            
            # 최근 데이터들 저장
            for i in range(min(5, len(vix_clean))):
                vix_date = vix_clean.index[-1-i].date()
                vix_value = vix_clean.iloc[-1-i]
                
                additional_data = json.dumps({
                    "data_source": "FRED (VIXCLS)",
                    "note": "Federal Reserve Economic Data"
                })
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )
                
                if success:
                    logger.info(f"Saved FRED VIX for {vix_date}: {vix_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating VIX with FRED: {e}", exc_info=True)
            return False

    def _update_vix_with_yahoo(self) -> bool:
        """Yahoo Finance에서 VIX 데이터 업데이트 (백업 방식)"""
        try:
            # Yahoo Finance ^VIX 데이터 가져오기 (API 호출 제한 고려)
            vix_data = self._fetch_yahoo_data_with_retry("^VIX", period="5d")
            
            if vix_data is None or vix_data.empty:
                logger.error("Failed to fetch VIX data from Yahoo Finance")
                return False
            
            # 최근 5일간의 데이터 처리
            recent_data = vix_data.tail(5)
            
            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                vix_date = date_idx.date()
                vix_value = row['Close']
                
                additional_data = json.dumps({
                    "data_source": "Yahoo Finance (^VIX)",
                    "note": "Yahoo Finance backup data"
                })
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )
                
                if success:
                    logger.info(f"Saved Yahoo VIX for {vix_date}: {vix_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating VIX with Yahoo: {e}", exc_info=True)
            return False

    def update_treasury_yield(self) -> bool:
        """
        FRED에서 10년 국채 수익률을 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting 10-Year Treasury Yield update...")
        
        try:
            # 최근 7일간의 데이터 가져오기
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            # FRED에서 10년 국채 수익률 가져오기
            treasury_data = web.DataReader('DGS10', 'fred', start_date, end_date)
            
            if treasury_data.empty:
                logger.warning("No Treasury yield data received from FRED")
                return False

            treasury_clean = treasury_data['DGS10'].dropna()
            
            # 최근 데이터들 저장
            for i in range(min(5, len(treasury_clean))):
                treasury_date = treasury_clean.index[-1-i].date()
                treasury_value = treasury_clean.iloc[-1-i]
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.US_10Y_TREASURY_YIELD,
                    data_date=treasury_date,
                    value=treasury_value
                )
                
                if success:
                    logger.info(f"Saved 10Y Treasury Yield for {treasury_date}: {treasury_value:.2f}%")

            return True

        except Exception as e:
            logger.error(f"Error updating Treasury yield: {e}", exc_info=True)
            return False

    def set_yahoo_settings(self, delay: float = 1.0, retry_count: int = 3, prefer_fred: bool = True):
        """
        Yahoo Finance API 설정을 조정합니다.
        
        Args:
            delay: Yahoo API 호출 간 지연 시간 (초)
            retry_count: 재시도 횟수
            prefer_fred: FRED를 우선 사용할지 여부
        """
        self.yahoo_request_delay = delay
        self.yahoo_retry_count = retry_count
        self.fred_preferred = prefer_fred
        logger.info(f"Yahoo settings updated: delay={delay}s, retry={retry_count}, prefer_fred={prefer_fred}")

    def update_all_indicators(self) -> Dict[str, bool]:
        """
        모든 지표를 업데이트합니다.
        Yahoo API 호출 제한을 고려하여 지연을 둡니다.
        
        Returns:
            Dict[str, bool]: 각 지표별 업데이트 성공 여부
        """
        logger.info("Starting update of all market indicators...")
        
        results = {}
        
        # 버핏 지수 업데이트 (Fed Z.1 우선, Yahoo 백업)
        results['buffett_indicator'] = self.update_buffett_indicator()
        
        # API 호출 제한 방지를 위한 지연
        if not self.fred_preferred:  # Yahoo 모드일 때만 지연
            logger.info("Delaying between indicator updates to respect API limits...")
            time.sleep(2.0)
        
        # VIX 업데이트 (FRED 우선, Yahoo 백업)
        results['vix'] = self.update_vix()
        
        # 추가 지연 (Yahoo 모드)
        if not self.fred_preferred:
            time.sleep(1.0)
        
        # 10년 국채 수익률 업데이트 (FRED만 사용)
        results['treasury_yield'] = self.update_treasury_yield()
        
        # TODO: 추후 추가될 지표들
        # results['put_call_ratio'] = self.update_put_call_ratio()
        # results['fear_greed_index'] = self.update_fear_greed_index()
        
        success_count = sum(results.values())
        total_count = len(results)
        
        # API 사용 통계 로깅
        yahoo_used = any('yahoo' in str(self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)) for _ in [0])
        logger.info(f"Market indicators update completed: {success_count}/{total_count} successful")
        logger.info(f"Data sources used: FRED={self.fred_preferred}, Yahoo_backup={'potentially' if not self.fred_preferred else 'if_needed'}")
        
        return results

    def get_data_source_stats(self) -> Dict[str, int]:
        """
        최근 데이터의 소스별 통계를 반환합니다.
        
        Returns:
            Dict[str, int]: 데이터 소스별 개수
        """
        stats = {
            'fred_buffett': 0,
            'yahoo_buffett': 0,
            'fred_vix': 0,
            'yahoo_vix': 0,
            'fred_treasury': 0
        }
        
        try:
            # 최근 10개 데이터 확인
            for indicator_type in [MarketIndicatorType.BUFFETT_INDICATOR, MarketIndicatorType.VIX, MarketIndicatorType.US_10Y_TREASURY_YIELD]:
                recent_data = self.repository.get_recent_market_data(indicator_type, limit=10)
                
                for data in recent_data:
                    if data.additional_data:
                        source_info = json.loads(data.additional_data)
                        source = source_info.get('data_source', '')
                        
                        if indicator_type == MarketIndicatorType.BUFFETT_INDICATOR:
                            if 'FRED' in source or 'Fed' in source:
                                stats['fred_buffett'] += 1
                            elif 'Yahoo' in source:
                                stats['yahoo_buffett'] += 1
                        elif indicator_type == MarketIndicatorType.VIX:
                            if 'FRED' in source:
                                stats['fred_vix'] += 1
                            elif 'Yahoo' in source:
                                stats['yahoo_vix'] += 1
                        elif indicator_type == MarketIndicatorType.US_10Y_TREASURY_YIELD:
                            stats['fred_treasury'] += 1
                            
        except Exception as e:
            logger.warning(f"Error getting data source stats: {e}")
            
        return stats

    def get_latest_buffett_indicator(self) -> Optional[float]:
        """최신 버핏 지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)
        return latest_data.value if latest_data else None

    def get_latest_vix(self) -> Optional[float]:
        """최신 VIX를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
        return latest_data.value if latest_data else None


if __name__ == '__main__':
    """테스트용 실행"""
    from infrastructure.logging import setup_logging
    setup_logging()
    
    service = MarketDataService()
    results = service.update_all_indicators()
    print("Update results:", results) 