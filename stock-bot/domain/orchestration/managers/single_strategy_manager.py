"""
정적 전략 매니저 - 정적 전략의 초기화, 관리, 교체를 담당
"""

from typing import Dict, List, Optional
import pandas as pd

from domain.signals.models.enums import StrategyType
from infrastructure.db.models.enums import TrendType
from domain.orchestration.factory import StrategyFactory
from domain.strategies.base import BaseStrategy
from domain.signals.models.strategy_result import StrategyResult
from domain.orchestration.utils.strategy_manager_utils import StrategyManagerUtils
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class SingleStrategyManager:
    """정적 전략들을 관리하는 매니저"""
    
    def __init__(self):
        self.active_strategies: Dict[StrategyType, BaseStrategy] = {}
        self.current_strategy: Optional[BaseStrategy] = None
    
    def initialize_strategies(self, strategy_types: Optional[List[StrategyType]] = None) -> int:
        """정적 전략들을 초기화합니다."""
        if strategy_types is None:
            # 기본적으로 모든 정적 전략을 로드
            from domain.orchestration.strategy_registry import strategy_registry
            strategy_names = strategy_registry.get_available_strategies("static")["static"]
            strategy_types = [StrategyType(name) for name in strategy_names]
        
        logger.info(f"정적 전략 초기화 시작: {len(strategy_types)}개 전략")
        
        success_count = 0
        for strategy_type in strategy_types:
            try:
                # factory를 직접 참조하여 전략 생성
                strategy = StrategyFactory.create_static_strategy(strategy_type)
                if StrategyManagerUtils.validate_strategy_initialization(strategy, strategy_type):
                    self.active_strategies[strategy_type] = strategy
                    success_count += 1
                    logger.info(f"정적 전략 초기화 성공: {strategy.get_name()}")
            except Exception as e:
                logger.error(f"정적 전략 초기화 실패 {strategy_type}: {e}")
                continue
        
        # 기본 전략 설정
        self._set_default_strategy()
        
        logger.info(f"정적 전략 초기화 완료: {success_count}/{len(strategy_types)} 성공")
        return success_count
    
    def _set_default_strategy(self):
        """기본 전략을 설정합니다."""
        if StrategyType.BALANCED in self.active_strategies:
            self.current_strategy = self.active_strategies[StrategyType.BALANCED]
        elif self.active_strategies:
            self.current_strategy = list(self.active_strategies.values())[0]
        
        if self.current_strategy:
            logger.info(f"기본 정적 전략 설정: {self.current_strategy.get_name()}")
    
    def add_strategy(self, strategy_type: StrategyType, strategy: Optional[BaseStrategy] = None) -> bool:
        """전략을 추가합니다."""
        if strategy is None:
            strategy = StrategyFactory.create_static_strategy(strategy_type)

        if not StrategyManagerUtils.validate_strategy_initialization(strategy, strategy_type):
            return False
        
        self.active_strategies[strategy_type] = strategy
        logger.info(f"정적 전략 추가 성공: {strategy.get_name()}")
        return True
    
    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """정적 전략을 교체합니다."""
        if strategy_type not in self.active_strategies:
            logger.warning(f"전략이 로드되지 않음: {strategy_type}")
            return False
        
        self.current_strategy = self.active_strategies[strategy_type]
        logger.info(f"정적 전략 교체 완료: {self.current_strategy.get_name()}")
        return True
    
    def set_strategy(self, strategy: BaseStrategy):
        """외부에서 생성된 정적 전략 객체를 직접 설정합니다."""
        if strategy is None:
            self._set_default_strategy()
            logger.info("전략이 None으로 설정되어 기본 전략으로 리셋합니다.")
            return
        
        self.current_strategy = strategy
        logger.info(f"정적 전략 직접 설정: {strategy.get_name()}")
    
    def analyze_with_current_strategy(self, 
                                    df_with_indicators: pd.DataFrame,
                                    ticker: str,
                                    market_trend: TrendType = TrendType.NEUTRAL,
                                    long_term_trend: TrendType = TrendType.NEUTRAL,
                                    daily_extra_indicators: Dict = None) -> Optional[StrategyResult]:
        """현재 정적 전략으로 분석합니다."""
        if not self.current_strategy:
            return None
        
        analysis_params = StrategyManagerUtils.get_analysis_parameters(
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
        analysis_params = StrategyManagerUtils.get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        results = {}
        for strategy_type, strategy in self.active_strategies.items():
            result = strategy.analyze(**analysis_params)
            results[strategy_type] = result
        return results
    
    def get_strategy_performance_summary(self) -> Dict[str, any]:
        """정적 전략별 성능 요약을 반환합니다."""
        performance = {}
        for strategy_type, strategy in self.active_strategies.items():
            performance[strategy_type.value] = strategy.get_performance_metrics()
        return performance
    
    def get_current_strategy_info(self) -> Optional[Dict[str, any]]:
        """현재 정적 전략 정보를 반환합니다."""
        if not self.current_strategy:
            return None
        
        return {
            "name": self.current_strategy.get_name(), 
            "type": self.current_strategy.strategy_type.value
        }
    
    def clear_current_strategy(self):
        """현재 전략을 해제합니다."""
        self.current_strategy = None
        logger.info("현재 정적 전략이 해제되었습니다.")
    
    @property
    def has_current_strategy(self) -> bool:
        """현재 활성화된 정적 전략이 있는지 확인합니다."""
        return self.current_strategy is not None
    
    @property
    def available_strategy_types(self) -> List[StrategyType]:
        """사용 가능한 정적 전략 타입들을 반환합니다."""
        return list(self.active_strategies.keys())