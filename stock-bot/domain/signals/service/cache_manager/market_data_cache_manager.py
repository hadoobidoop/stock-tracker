"""
시장 데이터 캐시 관리자
Market Data Cache Manager for efficient data storage and retrieval
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional, Any

from domain.indicators.calculator import (
    calculate_fibonacci_levels,
    calculate_daily_indicators
)
from domain.indicators.calculator import (
    validate_multi_timeframe_data,
    get_trend_direction_multi_timeframe
)
from domain.signals.service.shared import (
    DataProcessingHelper,
    IndicatorCalculationService
)
from domain.signals.service.shared.constants import (
    DataProcessingConstants,
    LoggingConstants
)
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MarketDataCache:
    """시장 데이터 캐시 데이터 클래스"""
    last_updated: Optional[date] = None
    market_trend: TrendType = TrendType.NEUTRAL
    daily_extras: Dict[str, Dict] = field(default_factory=dict)  # 피보나치 등 일봉 지표
    long_term_trends: Dict[str, TrendType] = field(default_factory=dict)
    long_term_trend_values: Dict[str, Dict] = field(default_factory=dict)
    daily_indicators: Dict[str, Any] = field(default_factory=dict)  # 일봉 기술적 지표
    multi_timeframe_analysis: Dict[str, Dict] = field(default_factory=dict)  # 다중 시간대 분석


class MarketDataCacheManager:
    """
    시장 데이터 캐시 관리자
    
    책임:
    - 일봉/시간봉 데이터 캐싱
    - 기술적 지표 계산 및 저장
    - 다중 시간대 분석 결과 관리
    - 캐시 무효화 및 갱신 관리
    """
    
    def __init__(self):
        self._cache = MarketDataCache()
        
    @property
    def cache(self) -> MarketDataCache:
        """캐시 데이터 반환"""
        return self._cache
    
    def is_cache_valid(self, current_date: date) -> bool:
        """캐시 유효성 검사"""
        return self._cache.last_updated == current_date
    
    def invalidate_cache(self):
        """캐시 무효화"""
        logger.info("캐시를 무효화합니다.")
        self._cache = MarketDataCache()
    
    def update_market_trend(self, market_trend: TrendType):
        """시장 추세 업데이트"""
        self._cache.market_trend = market_trend
        logger.debug(f"시장 추세 업데이트: {market_trend.value}")
    
    def update_daily_data_for_symbol(self, symbol: str, df_daily, df_hourly, stock_analysis_service):
        """개별 종목의 일봉 데이터 업데이트"""
        # 데이터 유효성 검사
        validated_df = DataProcessingHelper.validate_and_process_dataframe(
            df_daily, symbol, "일봉 데이터 업데이트", 
            DataProcessingConstants.MIN_DATA_LENGTH_FOR_FIBONACCI
        )
        
        if validated_df is None:
            return None
        
        # 피보나치 레벨 계산
        fib_data = DataProcessingHelper.safe_execute_with_logging(
            operation_name="피보나치 레벨 계산",
            symbol=symbol,
            operation_func=lambda: calculate_fibonacci_levels(validated_df)
        )
        
        if fib_data:
            self._cache.daily_extras[symbol] = fib_data
        
        # 일봉 기술적 지표 계산
        daily_indicators = IndicatorCalculationService.calculate_with_validation(
            validated_df, symbol, calculate_daily_indicators,
            DataProcessingConstants.MIN_DATA_LENGTH_FOR_BASIC_INDICATORS
        )
        
        if daily_indicators is not None:
            self._cache.daily_indicators[symbol] = daily_indicators
            logger.debug(LoggingConstants.DATA_UPDATE_SUCCESS.format(symbol=symbol))
            
        return daily_indicators
    
    def update_hourly_data_for_symbol(self, symbol: str, df_hourly, stock_analysis_service):
        """개별 종목의 시간봉 데이터 업데이트"""
        # 데이터 유효성 검사
        validated_df = DataProcessingHelper.validate_and_process_dataframe(
            df_hourly, symbol, "시간봉 데이터 업데이트"
        )
        
        if validated_df is None:
            return
        
        # 장기 추세 분석
        def get_long_term_trend():
            return stock_analysis_service.get_long_term_trend(validated_df)
        
        trend_result = DataProcessingHelper.safe_execute_with_logging(
            operation_name="장기 추세 분석",
            symbol=symbol,
            operation_func=get_long_term_trend,
            success_message=f"{{symbol}} 시간봉 데이터 캐시 업데이트 완료"
        )
        
        if trend_result:
            long_term_trend, trend_values = trend_result
            self._cache.long_term_trends[symbol] = long_term_trend
            self._cache.long_term_trend_values[symbol] = trend_values
    
    def update_multi_timeframe_analysis(self, symbol: str, df_daily, df_hourly):
        """다중 시간대 분석 업데이트"""
        try:
            if df_daily is not None and not df_daily.empty and df_hourly is not None and not df_hourly.empty:
                # 데이터 유효성 검증
                validation = validate_multi_timeframe_data(df_daily, df_hourly)
                
                if validation['sufficient_for_analysis']:
                    daily_indicators = self._cache.daily_indicators.get(symbol)
                    if daily_indicators is not None and not daily_indicators.empty:
                        trend_analysis = get_trend_direction_multi_timeframe(
                            daily_indicators, df_hourly
                        )
                        self._cache.multi_timeframe_analysis[symbol] = trend_analysis
                        logger.info(f"{symbol} 다중 시간대 분석 완료: {trend_analysis}")
                    else:
                        logger.warning(f"{symbol} 일봉 지표가 없어 다중 시간대 분석 건너뜀")
                else:
                    logger.warning(f"{symbol} 다중 시간대 분석을 위한 데이터 부족: {validation}")
                    
        except Exception as e:
            logger.error(f"{symbol} 다중 시간대 분석 업데이트 실패: {e}")
    
    def finalize_cache_update(self, current_date: date):
        """캐시 업데이트 완료 처리"""
        self._cache.last_updated = current_date
        logger.info("일일 데이터 캐시가 성공적으로 갱신되었습니다.")
    
    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """특정 종목의 캐시된 데이터 반환"""
        return {
            "daily_extras": self._cache.daily_extras.get(symbol, {}),
            "long_term_trend": self._cache.long_term_trends.get(symbol, TrendType.NEUTRAL),
            "long_term_trend_values": self._cache.long_term_trend_values.get(symbol, {}),
            "daily_indicators": self._cache.daily_indicators.get(symbol),
            "multi_timeframe_analysis": self._cache.multi_timeframe_analysis.get(symbol, {})
        }
    
    def get_enhanced_daily_extras(self, symbol: str) -> Dict[str, Any]:
        """강화된 일봉 추가 데이터 반환 (일봉 지표 + 다중 시간대 분석 포함)"""
        daily_extras = self._cache.daily_extras.get(symbol, {}).copy()
        
        # 일봉 지표 데이터 추가
        daily_indicators = self._cache.daily_indicators.get(symbol)
        if daily_indicators is not None and not daily_indicators.empty:
            daily_extras["daily_indicators"] = daily_indicators.iloc[-1].to_dict()
        
        # 다중 시간대 분석 결과 추가
        multi_timeframe_analysis = self._cache.multi_timeframe_analysis.get(symbol, {})
        if multi_timeframe_analysis:
            daily_extras["multi_timeframe"] = multi_timeframe_analysis
            
        return daily_extras
    
    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 반환"""
        return {
            "last_updated": self._cache.last_updated.isoformat() if self._cache.last_updated else None,
            "market_trend": self._cache.market_trend.value,
            "cached_symbols": {
                "daily_extras": len(self._cache.daily_extras),
                "long_term_trends": len(self._cache.long_term_trends),
                "daily_indicators": len(self._cache.daily_indicators),
                "multi_timeframe_analysis": len(self._cache.multi_timeframe_analysis)
            }
        }