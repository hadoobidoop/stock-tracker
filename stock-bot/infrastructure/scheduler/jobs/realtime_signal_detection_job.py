from datetime import datetime, date
from typing import Dict, List
import pandas as pd

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType
from infrastructure.db.repository.sql_technical_indicator_repository import SQLTechnicalIndicatorRepository
from infrastructure.db.repository.sql_trading_signal_repository import SQLTradingSignalRepository
from domain.analysis.service.signal_detection_service import DetectorFactory
from domain.analysis.utils import calculate_all_indicators, calculate_fibonacci_levels
from domain.analysis.repository.technical_indicator_repository import TechnicalIndicatorRepository
from domain.analysis.repository.trading_signal_repository import TradingSignalRepository
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from domain.analysis.config.analysis_settings import (
    SIGNAL_THRESHOLD, 
    REALTIME_SIGNAL_DETECTION
)

logger = get_logger(__name__)

# 전역 캐시 변수
daily_data_cache = {
    "last_updated": None,
    "market_trend": TrendType.NEUTRAL,
    "daily_extras": {},
    "long_term_trends": {},
    "long_term_trend_values": {}
}

# Repository 및 Service 인스턴스
technical_indicator_repo: TechnicalIndicatorRepository = SQLTechnicalIndicatorRepository()
trading_signal_repo: TradingSignalRepository = SQLTradingSignalRepository()
stock_repo: StockRepository = SQLStockRepository()
stock_analysis_service = StockAnalysisService(stock_repo)


def realtime_signal_detection_job():
    """
    [대폭 간소화됨] 1시간봉 데이터를 Yahoo Finance에서 직접 조회하여 실시간 신호를 감지합니다.
    Stock Service와 Repository 패턴을 활용하여 중복 로직을 제거했습니다.
    """
    global daily_data_cache

    current_et = stock_analysis_service.get_current_et_time()
    logger.info("JOB START: Real-time signal detection job (Hourly Analysis)...")

    stocks_to_analyze = stock_analysis_service.get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # Step 1: 캐시 업데이트 확인
    if daily_data_cache["last_updated"] != current_et.date():
        logger.info("Step 1: Refreshing daily data cache...")

        # 1.1. 시장 추세 업데이트
        daily_data_cache["market_trend"] = stock_analysis_service.get_market_trend()

        # 1.2. 일봉 및 시간봉 데이터 조회
        try:
            fib_lookback = REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"]
            lookback_period = REALTIME_SIGNAL_DETECTION["LOOKBACK_PERIOD_DAYS_FOR_INTRADAY"]
            
            all_daily_data = stock_analysis_service.get_stock_data_for_analysis(stocks_to_analyze, fib_lookback, '1d')
            all_hourly_data = stock_analysis_service.get_stock_data_for_analysis(stocks_to_analyze, lookback_period, '1h')

            for symbol in stocks_to_analyze:
                df_daily = all_daily_data.get(symbol)
                if df_daily is not None and not df_daily.empty:
                    # 기존 유틸리티 함수 사용
                    fib_data = calculate_fibonacci_levels(df_daily)
                    daily_data_cache["daily_extras"][symbol] = fib_data

                df_hourly = all_hourly_data.get(symbol)
                long_term_trend, trend_values = stock_analysis_service.get_long_term_trend(df_hourly)
                daily_data_cache["long_term_trends"][symbol] = long_term_trend
                daily_data_cache["long_term_trend_values"][symbol] = trend_values
                
        except Exception as e:
            logger.error(f"An error occurred during bulk data fetching for cache: {e}")

        daily_data_cache["last_updated"] = current_et.date()
        logger.info("Daily data cache has been successfully refreshed.")
    else:
        logger.info("Step 1: Using cached daily data.")

    market_trend = daily_data_cache["market_trend"]

    # Step 2: 실시간 신호 감지
    logger.info(f"Step 2: Starting HOURLY signal detection for {len(stocks_to_analyze)} stocks...")
    
    # 기존 detector 시스템 활용
    detector_factory = DetectorFactory()
    orchestrator = detector_factory.create_default_orchestrator()
    
    for symbol in stocks_to_analyze:
        try:
            # 2.1. 시간봉 데이터 조회
            lookback_period = REALTIME_SIGNAL_DETECTION["LOOKBACK_PERIOD_DAYS_FOR_INTRADAY"]
            df_hourly = stock_analysis_service.get_stock_data_for_analysis([symbol], lookback_period, '1h').get(symbol)
            
            if df_hourly is None or df_hourly.empty:
                logger.warning(f"No hourly data available for {symbol}")
                continue

            min_data_length = REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]
            if len(df_hourly) < min_data_length:
                logger.warning(f"Insufficient hourly data for {symbol}: {len(df_hourly)} < {min_data_length}")
                continue

            # 2.2. 기술적 지표 계산 (기존 유틸리티 함수 사용)
            df_with_indicators = calculate_all_indicators(df_hourly)
            
            if df_with_indicators.empty:
                logger.warning(f"Failed to calculate indicators for {symbol}")
                continue

            # 2.3. 기술적 지표 저장 (repository 패턴 사용)
            indicator_columns = [
                'SMA_5', 'SMA_20', 'SMA_60', 'RSI_14', 
                'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9',
                'STOCHk_14_3_3', 'STOCHd_14_3_3', 'ADX_14',
                'BBL_20_2_0', 'BBM_20_2_0', 'BBU_20_2_0',
                'ATR_14', 'Volume_SMA_20'
            ]
            
            available_columns = [col for col in indicator_columns if col in df_with_indicators.columns]
            indicators_df = df_with_indicators[available_columns].copy()
            technical_indicator_repo.save_indicators(indicators_df, symbol, '1h')

            # 2.4. 신호 감지 (기존 detector 시스템 활용)
            daily_extras = daily_data_cache["daily_extras"].get(symbol, {})
            long_term_trend = daily_data_cache["long_term_trends"].get(symbol, TrendType.NEUTRAL)
            long_term_trend_values = daily_data_cache["long_term_trend_values"].get(symbol, {})
            
            # 기존 orchestrator 사용
            signal_result = orchestrator.detect_signals(
                df_with_indicators, 
                symbol, 
                market_trend, 
                long_term_trend, 
                daily_extras
            )

            # 2.5. 신호 저장 (repository 패턴 사용)
            if signal_result and signal_result.get('score', 0) >= SIGNAL_THRESHOLD:
                from domain.analysis.models.trading_signal import TradingSignal
                
                signal = TradingSignal(
                    ticker=symbol,
                    signal_type=signal_result['type'],
                    signal_score=signal_result['score'],
                    timestamp_utc=current_et,
                    current_price=signal_result['current_price'],
                    market_trend=market_trend,
                    long_term_trend=long_term_trend,
                    trend_ref_close=long_term_trend_values.get('close'),
                    trend_ref_value=long_term_trend_values.get('sma'),
                    details=signal_result.get('details', []),
                    stop_loss_price=signal_result.get('stop_loss_price')
                )
                
                trading_signal_repo.save_signal(signal)

            # 2.6. 로깅
            if REALTIME_SIGNAL_DETECTION["LOG_DATA_LENGTH"]:
                log_count = REALTIME_SIGNAL_DETECTION["LOG_LAST_ROWS_COUNT"]
                logger.info(f"Processed {symbol}: {len(df_hourly)} hourly bars, "
                           f"last {log_count} rows: {df_hourly.tail(log_count)[['Close', 'Volume']].to_dict('records')}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue

    logger.info("JOB END: Real-time signal detection job completed.")


if __name__ == "__main__":
    realtime_signal_detection_job()
