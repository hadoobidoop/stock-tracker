"""
전략 매니저들에서 공통으로 사용하는 유틸리티 클래스
"""

from typing import Dict, Any, Optional

import pandas as pd

from domain.signals.models.enums import StrategyType
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class StrategyManagerUtils:
    """전략 매니저들의 공통 유틸리티 메서드를 제공하는 클래스"""
    
    @staticmethod
    def get_analysis_parameters(df_with_indicators: pd.DataFrame,
                               ticker: str,
                               market_trend: TrendType = TrendType.NEUTRAL,
                               long_term_trend: TrendType = TrendType.NEUTRAL,
                               daily_extra_indicators: Dict = None) -> Dict[str, Any]:
        """분석 파라미터를 표준화된 딕셔너리로 반환합니다."""
        return {
            'df_with_indicators': df_with_indicators,
            'ticker': ticker,
            'market_trend': market_trend,
            'long_term_trend': long_term_trend,
            'daily_extra_indicators': daily_extra_indicators
        }
    
    @staticmethod
    def create_strategy_info(strategy_type: StrategyType, 
                            strategy: BaseStrategy, 
                            is_current: bool = False,
                            strategy_class: str = "static") -> Dict[str, Any]:
        """전략 정보를 표준화된 형태로 생성합니다."""
        return {
            "type": strategy_type.value,
            "name": strategy.get_name(),
            "description": strategy.get_description(),
            "is_current": is_current,
            "strategy_class": strategy_class
        }
    
    @staticmethod
    def validate_strategy_initialization(strategy: Optional[BaseStrategy], 
                                       strategy_type: StrategyType) -> bool:
        """전략 초기화 결과를 검증합니다."""
        if not strategy or not strategy.initialize():
            logger.error(f"전략 초기화 실패: {strategy_type.value}")
            return False
        return True
    
    @staticmethod
    def standardize_analysis_input(df_with_indicators: pd.DataFrame,
                                  ticker: str,
                                  market_trend: TrendType = TrendType.NEUTRAL,
                                  long_term_trend: TrendType = TrendType.NEUTRAL,
                                  daily_extra_indicators: Dict = None) -> Dict[str, Any]:
        """분석 입력값을 표준화하고 검증합니다."""
        # 입력 검증
        if df_with_indicators.empty:
            logger.warning(f"빈 데이터프레임이 전달됨: {ticker}")
        
        if not ticker:
            logger.warning("티커가 제공되지 않음")
        
        # 표준화된 파라미터 반환
        return StrategyManagerUtils.get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
    
    @staticmethod
    def format_cache_key(ticker: str, analysis_type: str, **kwargs) -> str:
        """캐시 키를 표준화된 형태로 생성합니다."""
        base_key = f"{ticker}_{analysis_type}"
        if kwargs:
            # 추가 파라미터들을 정렬하여 일관된 키 생성
            params = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()))
            return f"{base_key}_{params}"
        return base_key