"""
정적 전략 매니저 - 정적 전략의 초기화, 관리, 교체를 담당
"""

from typing import Dict, List, Optional

import pandas as pd
from domain.orchestration.factory import StrategyFactory
from domain.orchestration.managers.base_strategy_manager import BaseStrategyManager
from domain.orchestration.utils.strategy_manager_utils import StrategyManagerUtils

from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class SingleStrategyManager(BaseStrategyManager[BaseStrategy, StrategyType]):
    """정적 전략들을 관리하는 매니저"""
    
    def __init__(self):
        super().__init__()
        # 하위 호환성을 위해 active_strategies 별칭 유지
        self.active_strategies = self.strategies
    
    def _create_strategy(self, strategy_key: StrategyType) -> Optional[BaseStrategy]:
        """정적 전략 생성"""
        return StrategyFactory.create_static_strategy(strategy_key)
    
    def _get_default_strategy_key(self) -> Optional[StrategyType]:
        """기본 정적 전략 키 반환"""
        return StrategyType.BALANCED if StrategyType.BALANCED in self.strategies else None
    
    def _get_strategy_display_name(self, strategy: BaseStrategy) -> str:
        """정적 전략 표시명 반환"""
        return strategy.get_name()
    
    def _validate_strategy(self, strategy: BaseStrategy, strategy_key: StrategyType) -> bool:
        """정적 전략 검증"""
        return StrategyManagerUtils.validate_strategy_initialization(strategy, strategy_key)
    
    def _get_available_strategy_keys(self) -> List[StrategyType]:
        """사용 가능한 정적 전략 키 목록 반환"""
        from domain.orchestration.strategy_registry import strategy_registry
        strategy_names = strategy_registry.get_available_strategies("static")["static"]
        return [StrategyType(name) for name in strategy_names]
    
    def add_strategy(self, strategy_type: StrategyType, strategy: Optional[BaseStrategy] = None) -> bool:
        """전략을 추가합니다."""
        if strategy is None:
            strategy = self._create_strategy(strategy_type)

        if not self._validate_strategy(strategy, strategy_type):
            return False
        
        self.strategies[strategy_type] = strategy
        logger.info(f"정적 전략 추가 성공: {self._get_strategy_display_name(strategy)}")
        return True
    
    def set_strategy(self, strategy: BaseStrategy):
        """외부에서 생성된 정적 전략 객체를 직접 설정합니다."""
        if strategy is None:
            self._set_default_strategy()
            logger.info("전략이 None으로 설정되어 기본 전략으로 리셋합니다.")
            return
        
        self.current_strategy = strategy
        logger.info(f"정적 전략 직접 설정: {self._get_strategy_display_name(strategy)}")
    
    def analyze_with_current_strategy(self, 
                                    df_with_indicators: pd.DataFrame,
                                    ticker: str,
                                    market_trend: TrendType = TrendType.NEUTRAL,
                                    long_term_trend: TrendType = TrendType.NEUTRAL,
                                    daily_extra_indicators: Dict = None) -> Optional[StrategyResult]:
        """현재 정적 전략으로 분석합니다."""
        if not self.current_strategy:
            return None
        
        analysis_params = self.get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        return self.current_strategy.analyze(**analysis_params)
    
    def analyze_with_all_strategies(self,
                                  df_with_indicators: pd.DataFrame,
                                  ticker: str,
                                  market_trend: TrendType = TrendType.NEUTRAL,
                                  long_term_trend: TrendType = TrendType.NEUTRAL,
                                  daily_extra_indicators: Dict = None) -> Dict[StrategyType, StrategyResult]:
        """모든 활성화된 정적 전략으로 분석합니다."""
        analysis_params = self.get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        results = {}
        for strategy_type, strategy in self.strategies.items():
            result = strategy.analyze(**analysis_params)
            results[strategy_type] = result
        return results
    
    def get_strategy_performance_summary(self) -> Dict[str, any]:
        """정적 전략별 성능 요약을 반환합니다."""
        performance = {}
        for strategy_type, strategy in self.strategies.items():
            performance[strategy_type.value] = strategy.get_performance_metrics()
        return performance
    
    def get_current_strategy_info(self) -> Optional[Dict[str, any]]:
        """현재 정적 전략 정보를 반환합니다."""
        if not self.current_strategy:
            return None
        
        return {
            "name": self._get_strategy_display_name(self.current_strategy), 
            "type": self.current_strategy.strategy_type.value
        }
    
    @property
    def available_strategy_types(self) -> List[StrategyType]:
        """사용 가능한 정적 전략 타입들을 반환합니다."""
        return list(self.strategies.keys())