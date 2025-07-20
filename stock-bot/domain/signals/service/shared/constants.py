"""
신호 감지 서비스 공통 상수
Shared constants for signal detection services
"""
from typing import List

# 데이터 처리 관련 상수
class DataProcessingConstants:
    """데이터 처리 관련 상수"""
    
    # 기본 OHLCV 컬럼
    BASIC_OHLCV_COLUMNS: List[str] = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    # 기술적 지표 계산에서 제외할 컬럼
    EXCLUDED_COLUMNS: List[str] = BASIC_OHLCV_COLUMNS
    
    # 최소 데이터 길이 요구사항
    MIN_DATA_LENGTH_FOR_BASIC_INDICATORS = 20
    MIN_DATA_LENGTH_FOR_SMA_60 = 60
    MIN_DATA_LENGTH_FOR_FIBONACCI = 30
    
    # 백테스팅 기본 설정
    DEFAULT_LOOKBACK_DAYS = 90  # 3개월


class CacheConstants:
    """캐시 관련 상수"""
    
    # 캐시 키 이름
    DAILY_EXTRAS_KEY = "daily_extras"
    LONG_TERM_TRENDS_KEY = "long_term_trends"
    LONG_TERM_TREND_VALUES_KEY = "long_term_trend_values"
    DAILY_INDICATORS_KEY = "daily_indicators"
    MULTI_TIMEFRAME_ANALYSIS_KEY = "multi_timeframe_analysis"
    
    # 강화된 일봉 데이터 키
    ENHANCED_DAILY_INDICATORS_KEY = "daily_indicators"
    ENHANCED_MULTI_TIMEFRAME_KEY = "multi_timeframe"


class SignalDetectionConstants:
    """신호 감지 관련 상수"""
    
    # 전략 타입
    STATIC_STRATEGY_TYPE = "static"
    DYNAMIC_STRATEGY_TYPE = "dynamic"
    
    # 신호 결과 키
    SIGNAL_SCORE_KEY = "score"
    SIGNAL_TYPE_KEY = "type"
    SIGNAL_DETAILS_KEY = "details"
    STOP_LOSS_PRICE_KEY = "stop_loss_price"
    
    # 신호 타입 값
    BUY_SIGNAL = "BUY"
    SELL_SIGNAL = "SELL"


class LoggingConstants:
    """로깅 관련 상수"""
    
    # 로그 메시지 템플릿
    DATA_UPDATE_SUCCESS = "{symbol} 데이터 캐시 업데이트 완료"
    DATA_UPDATE_FAILURE = "{symbol} 데이터 업데이트 실패: {error}"
    
    INDICATOR_CALCULATION_SUCCESS = "{symbol} 기술적 지표 계산 완료: {count} bars"
    INDICATOR_CALCULATION_FAILURE = "{symbol} 기술적 지표 계산 실패: {error}"
    
    CACHE_REFRESH_START = "Step 1: Refreshing daily data cache..."
    CACHE_USING_CACHED = "Step 1: Using cached daily data."
    
    SIGNAL_DETECTION_START = "Step 2: Starting HOURLY signal detection for {count} stocks..."