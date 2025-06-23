"""
시장 데이터 수집 및 관리 서비스
버핏 지수, VIX, 공포지수 등 다양한 시장 지표를 수집합니다.
"""
import pandas_datareader.data as web
import yfinance as yf
import requests
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import json

from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """시장 데이터 수집 및 관리 서비스"""

    def __init__(self):
        self.repository = SQLMarketDataRepository()

    def update_buffett_indicator(self) -> bool:
        """
        Federal Reserve Z.1 Financial Accounts 데이터를 사용하여 버핏 지수를 계산하고 저장합니다.
        
        전체 미국 주식시장 시가총액 / GDP 를 계산합니다.
        VTI 대신 Fed의 공식 시장 시가총액 데이터를 사용합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Buffett Indicator update using Fed Z.1 data...")
        
        try:
            # 1. GDP 데이터 가져오기 (FRED)
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
            
            # 2. Federal Reserve Z.1 Financial Accounts 데이터 가져오기
            # Nonfinancial corporate business; corporate equities; liability, Level
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
            
            # 3. 최근 5일간의 데이터로 버핏 지수 계산
            # GDP는 분기별이므로 시장 데이터의 최근 5개 포인트 사용
            for i in range(min(5, len(market_clean))):
                market_date = market_clean.index[-1-i].date()
                market_cap_millions = market_clean.iloc[-1-i]
                market_cap_billions = market_cap_millions / 1000
                
                # 버핏 지수 계산
                # 시장 시가총액과 GDP 모두 십억 달러 단위
                buffett_ratio = (market_cap_billions / latest_gdp) * 100
                
                # 데이터베이스에 저장
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
                else:
                    logger.error(f"Failed to save Buffett Indicator for {market_date}")

            return True

        except Exception as e:
            logger.error(f"Error updating Buffett Indicator: {e}", exc_info=True)
            return False

    def update_vix(self) -> bool:
        """
        FRED에서 VIX 데이터를 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting VIX update...")
        
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
                
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value
                )
                
                if success:
                    logger.info(f"Saved VIX for {vix_date}: {vix_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating VIX: {e}", exc_info=True)
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

    def update_all_indicators(self) -> Dict[str, bool]:
        """
        모든 지표를 업데이트합니다.
        
        Returns:
            Dict[str, bool]: 각 지표별 업데이트 성공 여부
        """
        logger.info("Starting update of all market indicators...")
        
        results = {}
        
        # 버핏 지수 업데이트 (Fed Z.1 기반)
        results['buffett_indicator'] = self.update_buffett_indicator()
        
        # VIX 업데이트
        results['vix'] = self.update_vix()
        
        # 10년 국채 수익률 업데이트
        results['treasury_yield'] = self.update_treasury_yield()
        
        # TODO: 추후 추가될 지표들
        # results['put_call_ratio'] = self.update_put_call_ratio()
        # results['fear_greed_index'] = self.update_fear_greed_index()
        
        success_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"Market indicators update completed: {success_count}/{total_count} successful")
        
        return results

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