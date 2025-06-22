from datetime import datetime, date
from typing import Dict, List
import pandas as pd

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType
from infrastructure.db.repository.sql_technical_indicator_repository import SQLTechnicalIndicatorRepository
from infrastructure.db.repository.sql_trading_signal_repository import SQLTradingSignalRepository

# 새로운 전략 시스템 import
from domain.analysis.service.signal_detection_service import EnhancedSignalDetectionService, DetectorFactory

from domain.analysis.utils import (
    calculate_all_indicators, 
    calculate_fibonacci_levels,
    calculate_multi_timeframe_indicators,
    validate_multi_timeframe_data,
    get_trend_direction_multi_timeframe
)
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

# 전역 캐시 변수 (다중 시간대 분석용으로 확장)
daily_data_cache = {
    "last_updated": None,
    "market_trend": TrendType.NEUTRAL,
    "daily_extras": {},  # 피보나치 등 기존 일봉 지표
    "long_term_trends": {},
    "long_term_trend_values": {},
    "daily_indicators": {},  # 새로 추가: 일봉 기술적 지표
    "multi_timeframe_analysis": {}  # 새로 추가: 다중 시간대 분석 결과
}

# Repository 및 Service 인스턴스
technical_indicator_repo: TechnicalIndicatorRepository = SQLTechnicalIndicatorRepository()
trading_signal_repo: TradingSignalRepository = SQLTradingSignalRepository()
stock_repo: StockRepository = SQLStockRepository()
stock_analysis_service = StockAnalysisService(stock_repo)

def get_strategy_service() -> EnhancedSignalDetectionService:
    """main.py에서 초기화된 전략 서비스를 가져옵니다."""
    try:
        from main import get_strategy_service
        return get_strategy_service()
    except Exception as e:
        logger.warning(f"새로운 전략 서비스를 가져올 수 없음: {e}. 레거시 시스템 사용.")
        return None


def realtime_signal_detection_job():
    """
    [전략 시스템 통합] 새로운 전략 시스템을 사용하여 실시간 신호를 감지합니다.
    """
    global daily_data_cache

    current_et = stock_analysis_service.get_current_et_time()
    logger.info("JOB START: Real-time signal detection job (Enhanced Strategy System)...")

    stocks_to_analyze = stock_analysis_service.get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # 새로운 전략 서비스 가져오기
    strategy_service = get_strategy_service()
    use_new_system = strategy_service is not None

    if use_new_system:
        logger.info("✅ 새로운 전략 시스템 사용")
        current_strategy_info = strategy_service.get_current_strategy_info()
        logger.info(f"현재 활성 전략: {current_strategy_info}")
    else:
        logger.info("⚠️  레거시 시스템 사용 (새로운 전략 시스템 비활성화)")
        # 레거시 시스템을 위한 백업 - 기존 DetectorFactory 사용
        detector_factory = DetectorFactory()
        orchestrator = detector_factory.create_default_orchestrator()

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
                df_hourly = all_hourly_data.get(symbol)
                
                if df_daily is not None and not df_daily.empty:
                    # 기존 피보나치 레벨 계산
                    fib_data = calculate_fibonacci_levels(df_daily)
                    daily_data_cache["daily_extras"][symbol] = fib_data
                    
                    # 새로 추가: 일봉 기술적 지표 계산
                    from domain.analysis.utils import calculate_daily_indicators
                    daily_indicators = calculate_daily_indicators(df_daily)
                    daily_data_cache["daily_indicators"][symbol] = daily_indicators
                    
                    # 일봉 기술적 지표도 DB에 저장
                    if daily_indicators is not None and not daily_indicators.empty:
                        excluded_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        daily_indicator_columns = [col for col in daily_indicators.columns 
                                                if col not in excluded_columns]
                        latest_daily_indicators = daily_indicators[daily_indicator_columns].iloc[-1:].copy()
                        technical_indicator_repo.save_indicators(latest_daily_indicators, symbol, '1d')
                    
                    # 새로운 전략 시스템인 경우 지표 프리컴퓨팅
                    if use_new_system:
                        try:
                            strategy_service.precompute_indicators_for_ticker(symbol, df_daily)
                            logger.debug(f"Daily indicators precomputed for {symbol}")
                        except Exception as e:
                            logger.warning(f"Daily indicator precomputing failed for {symbol}: {e}")
                    
                    logger.debug(f"Calculated and stored daily indicators for {symbol}: {len(daily_indicators)} bars")

                if df_hourly is not None and not df_hourly.empty:
                    long_term_trend, trend_values = stock_analysis_service.get_long_term_trend(df_hourly)
                    daily_data_cache["long_term_trends"][symbol] = long_term_trend
                    daily_data_cache["long_term_trend_values"][symbol] = trend_values
                    
                    # 다중 시간대 분석 (일봉과 시간봉 데이터가 모두 있을 때)
                    if df_daily is not None and not df_daily.empty:
                        validation = validate_multi_timeframe_data(df_daily, df_hourly)
                        if validation['sufficient_for_analysis']:
                            trend_analysis = get_trend_direction_multi_timeframe(
                                daily_data_cache["daily_indicators"][symbol], 
                                df_hourly
                            )
                            daily_data_cache["multi_timeframe_analysis"][symbol] = trend_analysis
                            logger.info(f"Multi-timeframe analysis for {symbol}: {trend_analysis}")
                        else:
                            logger.warning(f"Insufficient data for multi-timeframe analysis for {symbol}: {validation}")
                else:
                    logger.warning(f"No hourly data for {symbol}")
                
        except Exception as e:
            logger.error(f"An error occurred during bulk data fetching for cache: {e}")

        daily_data_cache["last_updated"] = current_et.date()
        logger.info("Daily data cache has been successfully refreshed.")
    else:
        logger.info("Step 1: Using cached daily data.")

    market_trend = daily_data_cache["market_trend"]

    # Step 2: 실시간 신호 감지
    logger.info(f"Step 2: Starting HOURLY signal detection for {len(stocks_to_analyze)} stocks...")
    
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
            
            # 최소한의 기술적 지표 계산을 위해 추가 검증
            if len(df_hourly) < 60:  # SMA_60을 위한 최소 길이
                logger.warning(f"Insufficient data for SMA_60 calculation for {symbol}: {len(df_hourly)} < 60")
                # SMA_60 없이도 다른 지표들을 계산할 수 있도록 계속 진행

            # 2.2. 기술적 지표 계산
            if use_new_system:
                # 새로운 전략 시스템: 지표 프리컴퓨팅 사용
                df_with_indicators = strategy_service.precompute_indicators_for_ticker(symbol, df_hourly)
            else:
                # 레거시 시스템: 기존 방식
                df_with_indicators = calculate_all_indicators(df_hourly)
            
            if df_with_indicators.empty:
                logger.warning(f"Failed to calculate indicators for {symbol}")
                continue
            
            # 디버깅: 계산된 지표들의 유효성 확인
            logger.debug(f"Calculated indicators for {symbol}:")
            for col in df_with_indicators.columns:
                if col not in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    valid_count = df_with_indicators[col].notna().sum()
                    total_count = len(df_with_indicators)
                    logger.debug(f"  {col}: {valid_count}/{total_count} valid values")
                    if valid_count > 0:
                        last_value = df_with_indicators[col].iloc[-1]
                        logger.debug(f"    Last value: {last_value}")
                    else:
                        logger.warning(f"    All values are null for {col}")

            # 2.3. 기술적 지표 저장 (repository 패턴 사용) - 자동화된 컬럼 선택
            excluded_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            indicator_columns = [col for col in df_with_indicators.columns 
                                if col not in excluded_columns]

            # 최신 시점만 저장 (효율성 개선)
            latest_indicators_df = df_with_indicators[indicator_columns].iloc[-1:].copy()
            technical_indicator_repo.save_indicators(latest_indicators_df, symbol, '1h')

            logger.info(f"Successfully saved/updated {len(indicator_columns)} technical indicators for {symbol}")

            # 2.4. 신호 감지
            daily_extras = daily_data_cache["daily_extras"].get(symbol, {})
            long_term_trend = daily_data_cache["long_term_trends"].get(symbol, TrendType.NEUTRAL)
            long_term_trend_values = daily_data_cache["long_term_trend_values"].get(symbol, {})
            
            # 다중 시간대 분석 결과 추가
            daily_indicators = daily_data_cache["daily_indicators"].get(symbol)
            multi_timeframe_analysis = daily_data_cache["multi_timeframe_analysis"].get(symbol, {})
            
            # daily_extras에 일봉 지표 데이터 추가
            enhanced_daily_extras = daily_extras.copy()
            if daily_indicators is not None and not daily_indicators.empty:
                enhanced_daily_extras["daily_indicators"] = daily_indicators.iloc[-1].to_dict()
            
            # 다중 시간대 분석 결과 추가
            if multi_timeframe_analysis:
                enhanced_daily_extras["multi_timeframe"] = multi_timeframe_analysis

            if use_new_system:
                # 새로운 전략 시스템 사용
                try:
                    strategy_result = strategy_service.detect_signals_with_strategy(
                        df_with_indicators, symbol, None,  # 현재 활성 전략 사용
                        market_trend, long_term_trend, enhanced_daily_extras
                    )
                    
                    logger.info(f"[NEW] Strategy result for {symbol}: "
                              f"Strategy={strategy_result.strategy_name}, "
                              f"Score={strategy_result.total_score:.2f}, "
                              f"Signal={'YES' if strategy_result.has_signal else 'NO'}, "
                              f"Strength={strategy_result.signal_strength}")
                    
                    # 신호가 있으면 저장
                    if strategy_result.has_signal and strategy_result.signal:
                        try:
                            trading_signal_repo.save_signal(strategy_result.signal)
                            logger.info(f"✅ Trading signal saved for {symbol} using {strategy_result.strategy_name}")
                        except Exception as e:
                            logger.error(f"Failed to save trading signal for {symbol}: {e}")
                    
                    # 다중 시간대 필터 적용 (기존 로직 유지)
                    if multi_timeframe_analysis:
                        # 기존 신호 결과를 Dict 형태로 변환하여 필터 적용
                        legacy_signal_result = {
                            'score': strategy_result.total_score,
                            'type': 'BUY' if strategy_result.has_signal else None,
                            'details': strategy_result.signals_detected,
                            'stop_loss_price': None  # 필요시 구현
                        }
                        
                        filtered_result = _apply_multi_timeframe_filter(legacy_signal_result, multi_timeframe_analysis)
                        
                        if filtered_result != legacy_signal_result:
                            logger.info(f"Multi-timeframe filter applied for {symbol}: "
                                      f"Score {strategy_result.total_score:.2f} -> {filtered_result.get('score', 0):.2f}")
                
                except Exception as e:
                    logger.error(f"Error in new strategy system for {symbol}: {e}")
                    logger.info(f"Falling back to legacy system for {symbol}")
                    use_new_system = False  # 이 심볼에 대해서는 레거시 사용
            
            if not use_new_system:
                # 레거시 시스템 사용 (백업)
                signal_result = orchestrator.detect_signals(
                    df_with_indicators, symbol, market_trend, long_term_trend, enhanced_daily_extras
                )
                
                if signal_result and signal_result.get('score', 0) >= SIGNAL_THRESHOLD:
                    logger.info(f"[LEGACY] Signal detected for {symbol}: score={signal_result.get('score', 0):.2f}")
                    
                    # 다중 시간대 필터 적용
                    if multi_timeframe_analysis:
                        signal_result = _apply_multi_timeframe_filter(signal_result, multi_timeframe_analysis)
                    
                    # 신호 저장 로직 (기존)
                    try:
                        from domain.analysis.models.trading_signal import TradingSignal, SignalType
                        from domain.analysis.models.trading_signal import SignalEvidence
                        
                        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL
                        evidence = SignalEvidence(
                            signal_timestamp=current_et,
                            ticker=symbol,
                            signal_type=signal_result.get('type', 'BUY'),
                            final_score=int(signal_result.get('score', 0)),
                            raw_signals=signal_result.get('details', []),
                            applied_filters=['Legacy system'],
                            score_adjustments=[f"Market trend: {market_trend.value}, Long term: {long_term_trend.value}"]
                        )
                        
                        trading_signal = TradingSignal(
                            signal_id=None,
                            ticker=symbol,
                            signal_type=signal_type,
                            signal_score=signal_result.get('score', 0),
                            timestamp_utc=current_et,
                            current_price=df_with_indicators['Close'].iloc[-1],
                            market_trend=market_trend.value,
                            long_term_trend=long_term_trend.value,
                            details=signal_result.get('details', []),
                            stop_loss_price=signal_result.get('stop_loss_price'),
                            evidence=evidence
                        )
                        
                        trading_signal_repo.save_signal(trading_signal)
                        logger.info(f"✅ Legacy trading signal saved for {symbol}")
                        
                    except Exception as e:
                        logger.error(f"Failed to save legacy trading signal for {symbol}: {e}")
                else:
                    logger.debug(f"[LEGACY] No significant signal for {symbol}: score={signal_result.get('score', 0) if signal_result else 0:.2f}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue

    # Step 3: 작업 완료 로그
    if use_new_system:
        # 새로운 전략 시스템 성능 모니터링
        try:
            performance = strategy_service.get_strategy_performance_summary()
            logger.info(f"Strategy performance summary: {performance}")
        except Exception as e:
            logger.warning(f"Failed to get strategy performance summary: {e}")

    logger.info("JOB END: Real-time signal detection job completed successfully.")


def _apply_multi_timeframe_filter(signal_result: Dict, multi_timeframe_analysis: Dict) -> Dict:
    """
    다중 시간대 분석 결과를 바탕으로 신호를 필터링합니다.
    
    Args:
        signal_result: 기존 신호 감지 결과
        multi_timeframe_analysis: 다중 시간대 분석 결과
    
    Returns:
        Dict: 필터링된 신호 결과 (조건에 맞지 않으면 빈 딕셔너리)
    """
    try:
        if not signal_result or not multi_timeframe_analysis:
            return signal_result
        
        signal_type = signal_result.get('type')
        consensus = multi_timeframe_analysis.get('consensus', 'NEUTRAL')
        daily_trend = multi_timeframe_analysis.get('daily_trend', 'NEUTRAL')
        hourly_trend = multi_timeframe_analysis.get('hourly_trend', 'NEUTRAL')
        
        # 매수 신호 필터링
        if signal_type == 'BUY':
            # 강한 매수 조건: 일봉과 시간봉 모두 상승
            if consensus == 'BULLISH':
                signal_result['score'] = int(signal_result['score'] * 1.2)  # 신뢰도 증가
                signal_result['details'].append("다중시간대 상승 확인으로 신호 강화")
                return signal_result
            
            # 약한 매수 조건: 시간봉만 상승 (일봉 중립)
            elif hourly_trend == 'BULLISH' and daily_trend == 'NEUTRAL':
                signal_result['score'] = int(signal_result['score'] * 0.9)  # 약간 감소
                signal_result['details'].append("단기 상승 신호 (장기 추세 중립)")
                return signal_result
            
            # 위험한 매수: 일봉 하락 중 시간봉 상승 (거짓 신호 가능성)
            elif daily_trend == 'BEARISH':
                logger.warning(f"Filtered out BUY signal due to bearish daily trend")
                return {}  # 신호 거부
        
        # 매도 신호 필터링
        elif signal_type == 'SELL':
            # 강한 매도 조건: 일봉과 시간봉 모두 하락
            if consensus == 'BEARISH':
                signal_result['score'] = int(signal_result['score'] * 1.2)  # 신뢰도 증가
                signal_result['details'].append("다중시간대 하락 확인으로 신호 강화")
                return signal_result
            
            # 약한 매도 조건: 시간봉만 하락 (일봉 중립)
            elif hourly_trend == 'BEARISH' and daily_trend == 'NEUTRAL':
                signal_result['score'] = int(signal_result['score'] * 0.9)  # 약간 감소
                signal_result['details'].append("단기 하락 신호 (장기 추세 중립)")
                return signal_result
            
            # 위험한 매도: 일봉 상승 중 시간봉 하락 (거짓 신호 가능성)
            elif daily_trend == 'BULLISH':
                logger.warning(f"Filtered out SELL signal due to bullish daily trend")
                return {}  # 신호 거부
        
        return signal_result
        
    except Exception as e:
        logger.error(f"Error in multi-timeframe filter: {e}")
        return signal_result  # 에러 발생시 원본 신호 반환


if __name__ == "__main__":
    from infrastructure.logging import setup_logging
    setup_logging()
    realtime_signal_detection_job()
