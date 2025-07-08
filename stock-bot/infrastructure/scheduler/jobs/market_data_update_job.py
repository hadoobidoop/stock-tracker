"""
시장 데이터 업데이트 배치 잡
버핏 지수, VIX, 10년 국채 수익률 등 시장 지표들을 정기적으로 수집합니다.
"""
from datetime import datetime

from infrastructure.logging import get_logger
from domain.stock.service.market_data_service import MarketDataService

logger = get_logger(__name__)


def market_data_update_job():
    """
    시장 데이터를 업데이트하는 스케줄링 작업입니다.
    
    수집하는 지표:
    - 버핏 지수 (Wilshire 5000 / GDP)
    - VIX (공포지수)
    - 10년 국채 수익률
    - 추후 확장: Put/Call 비율, Fear & Greed Index 등
    """
    logger.info("JOB START: Market data update...")
    
    try:
        service = MarketDataService()
        
        # 모든 시장 지표 업데이트
        results = service.update_all_indicators()
        
        # 결과 로깅
        success_indicators = [indicator for indicator, success in results.items() if success]
        failed_indicators = [indicator for indicator, success in results.items() if not success]
        
        if success_indicators:
            logger.info(f"Successfully updated indicators: {', '.join(success_indicators)}")
        
        if failed_indicators:
            logger.warning(f"Failed to update indicators: {', '.join(failed_indicators)}")
            
        # 최신 값들 로깅 (확인용)
        latest_buffett = service.get_latest_buffett_indicator()
        latest_vix = service.get_latest_vix()
        latest_gold = service.get_latest_gold_price()
        latest_oil = service.get_latest_crude_oil_price()
        latest_sp500 = service.get_latest_sp500_index()
        latest_treasury = service.get_latest_treasury_yield()
        latest_put_call = service.get_latest_put_call_ratio()
        latest_fear_greed = service.get_latest_fear_greed_index()
        
        if latest_buffett:
            logger.info(f"Latest Buffett Indicator: {latest_buffett:.3f}%")
        if latest_vix:
            logger.info(f"Latest VIX: {latest_vix:.3f}")
        if latest_gold:
            logger.info(f"Latest Gold Price: ${latest_gold:.3f}")
        if latest_oil:
            logger.info(f"Latest Crude Oil: ${latest_oil:.3f}")
        if latest_sp500:
            logger.info(f"Latest S&P 500: {latest_sp500:.3f}")
        if latest_treasury:
            logger.info(f"Latest 10Y Treasury: {latest_treasury:.3f}%")
        if latest_put_call:
            logger.info(f"Latest Put/Call Ratio: {latest_put_call:.3f}")
        if latest_fear_greed:
            logger.info(f"Latest Fear & Greed Index: {latest_fear_greed:.3f}")
            
        logger.info("JOB END: Market data update completed successfully.")
        
    except Exception as e:
        logger.error(f"Market data update job failed: {e}", exc_info=True)


if __name__ == '__main__':
    """테스트용 실행"""
    from infrastructure.logging import setup_logging
    setup_logging()
    market_data_update_job() 