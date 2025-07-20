"""
전략 오케스트레이터 - 모든 전략 매니저들을 조율하는 최상위 facade
"""

from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd

from domain.orchestration.managers.dynamic_strategy_manager import DynamicStrategyManager
from domain.signals.models.enums import StrategyType
from domain.orchestration.managers.single_strategy_manager import SingleStrategyManager
from domain.orchestration.managers.strategy_mix_manager import StrategyMixManager
from domain.orchestration.managers.auto_strategy_selector import AutoStrategySelector
from domain.strategies.dynamic.dynamic_strategy_manager import DynamicCompositeStrategy
from domain.strategies.base import BaseStrategy
from domain.signals.models.strategy_result import StrategyResult
from infrastructure.db.models.enums import TrendType
from domain.orchestration.utils.strategy_manager_utils import StrategyManagerUtils
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class StrategyOrchestrator:
    """
    전략 오케스트레이터 - 여러 전략을 관리하고 동적으로 교체할 수 있는 시스템
    
    이 클래스는 사용자가 원하는 "갈아끼우며 사용할 수 있는" 전략 시스템을 제공합니다.
    기존 StrategyManager의 public API를 유지하면서 내부적으로는 분리된 매니저들에게 위임합니다.
    """
    
    def __init__(self):
        # 분리된 매니저들
        self.single_manager = SingleStrategyManager()
        self.mix_manager = StrategyMixManager()
        self.auto_selector = AutoStrategySelector()
        self.dynamic_manager = DynamicStrategyManager()
        
        # 성능 관리
        self.performance_history: List[Dict] = []
        
        # 자동 선택기에 콜백 함수들 설정
        self._setup_auto_selector_callbacks()
    
    def _setup_auto_selector_callbacks(self):
        """자동 전략 선택기에 필요한 콜백 함수들을 설정합니다."""
        self.auto_selector.set_strategy_switchers(
            static_switcher=self.switch_strategy,
            dynamic_switcher=self.switch_to_dynamic_strategy,
            current_strategy_getter=lambda: self.single_manager.current_strategy,
            current_dynamic_strategy_getter=lambda: self.dynamic_manager.current_strategy
        )
    
    # ============================================================================
    # 전략 초기화 및 관리
    # ============================================================================
        
    def initialize_strategies(self, strategy_types: Optional[List[StrategyType]] = None) -> bool:
        """전략들을 초기화합니다."""
        logger.info("전략 오케스트레이터 초기화 시작")
        
        # 정적 전략 초기화
        static_success_count = self.single_manager.initialize_strategies(strategy_types)
        
        # 동적 전략 초기화 (위임)
        dynamic_success_count = self.dynamic_manager.initialize()
        
        total_success = static_success_count + dynamic_success_count
        logger.info(f"전략 오케스트레이터 초기화 완료: {static_success_count} 정적 전략, {dynamic_success_count} 동적 전략")
        
        return total_success > 0
    
    def add_strategy(self, strategy_type: StrategyType, strategy: Optional[BaseStrategy] = None) -> bool:
        """전략 추가"""
        return self.single_manager.add_strategy(strategy_type, strategy)
    
    def set_strategy(self, strategy: Optional[BaseStrategy]):
        """
        외부에서 생성된 전략 객체를 직접 설정합니다. (주로 동적 전략 백테스팅용)
        """
        if strategy is None:
            # None으로 설정하면 기본 정적 전략으로 리셋
            self._reset_to_default_static_strategy()
            logger.info("전략이 None으로 설정되어 기본 전략으로 리셋합니다.")
            return

        # 전략의 종류에 따라 적절한 매니저에 할당
        if isinstance(strategy, DynamicCompositeStrategy):
            self._disable_other_modes_except_dynamic()
            self.dynamic_manager.current_strategy = strategy
            logger.info(f"동적 전략 직접 설정: {strategy.strategy_name}")
        elif isinstance(strategy, BaseStrategy):
            # 정적 전략인 경우
            self._disable_other_modes_except_static()
            self.single_manager.set_strategy(strategy)
            logger.info(f"정적 전략 직접 설정: {strategy.get_name()}")
        else:
            logger.error(f"알 수 없는 타입의 전략 객체입니다: {type(strategy)}")

    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """정적 전략 교체"""
        if self.single_manager.switch_strategy(strategy_type):
            self._disable_other_modes_except_static()
            return True
        return False
    
    def set_strategy_mix(self, mix_name: str) -> bool:
        """Static Strategy Mix(조합) 설정"""
        if self.mix_manager.set_strategy_mix(mix_name):
            self._disable_other_modes_except_mix()
            return True
        return False

    def switch_to_dynamic_strategy(self, strategy_name: str) -> bool:
        """동적 전략으로 교체"""
        if self.dynamic_manager.switch_strategy(strategy_name):
            self._disable_other_modes_except_dynamic()
            return True
        return False
    
    def _disable_other_modes_except_static(self):
        """정적 전략 모드 외 다른 모든 모드를 비활성화합니다."""
        self.dynamic_manager.current_strategy = None
        self.mix_manager.clear_current_mix()
    
    def _disable_other_modes_except_dynamic(self):
        """동적 전략 모드 외 다른 모든 모드를 비활성화합니다."""
        self.single_manager.clear_current_strategy()
        self.mix_manager.clear_current_mix()
    
    def _disable_other_modes_except_mix(self):
        """믹스 모드 외 다른 모든 모드를 비활성화합니다."""
        self.single_manager.clear_current_strategy()
        self.dynamic_manager.current_strategy = None
    
    def _reset_to_default_static_strategy(self):
        """기본 정적 전략으로 리셋합니다."""
        self.single_manager._set_default_strategy()
        self._disable_other_modes_except_static()
    
    @property
    def active_strategy(self) -> Optional[BaseStrategy]:
        """현재 활성화된 단일 전략 객체를 반환합니다 (동적 또는 정적)."""
        if self.dynamic_manager.current_strategy:
            return self.dynamic_manager.current_strategy
        if self.single_manager.current_strategy:
            return self.single_manager.current_strategy
        return None

    # ============================================================================
    # 전략 분석 및 실행
    # ============================================================================

    def analyze_with_current_strategy(self, 
                                    df_with_indicators: pd.DataFrame,
                                    ticker: str,
                                    market_trend: TrendType = TrendType.NEUTRAL,
                                    long_term_trend: TrendType = TrendType.NEUTRAL,
                                    daily_extra_indicators: Dict = None) -> StrategyResult:
        """현재 활성화된 전략으로 분석합니다."""
        
        # 자동 전략 선택이 활성화된 경우
        if self.auto_selector.is_auto_selection_enabled:
            self.auto_selector.auto_select_strategy(market_trend, df_with_indicators)
        
        # 분석 파라미터 표준화 및 검증
        analysis_params = StrategyManagerUtils.standardize_analysis_input(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        # 실제 분석을 수행할 전략 결정
        if self.dynamic_manager.current_strategy:
            return self.dynamic_manager.current_strategy.analyze(**analysis_params)
        elif self.single_manager.has_current_strategy:
            return self.single_manager.analyze_with_current_strategy(**analysis_params)
        elif self.mix_manager.has_current_mix:
            return self.mix_manager.analyze_with_strategy_mix(
                self.single_manager.active_strategies, **analysis_params
            )
        else:
            raise RuntimeError("활성화된 전략이 없습니다.")
    
    def analyze_with_all_strategies(self,
                                  df_with_indicators: pd.DataFrame,
                                  ticker: str,
                                  market_trend: TrendType = TrendType.NEUTRAL,
                                  long_term_trend: TrendType = TrendType.NEUTRAL,
                                  daily_extra_indicators: Dict = None) -> Dict[StrategyType, StrategyResult]:
        """모든 활성화된 정적 전략으로 분석합니다."""
        return self.single_manager.analyze_with_all_strategies(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )

    # ============================================================================
    # 자동 전략 선택 및 성능 관리
    # ============================================================================
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """전략별 성능 요약을 반환합니다."""
        return self.single_manager.get_strategy_performance_summary()
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """현재 전략 정보를 반환합니다."""
        if self.dynamic_manager.current_strategy:
            return {
                "mode": "dynamic", 
                "strategy": self.dynamic_manager.get_strategy_info()
            }
        elif self.mix_manager.has_current_mix:
            return {
                "mode": "mix", 
                "mix_config": self.mix_manager.get_current_mix_info()
            }
        elif self.single_manager.has_current_strategy:
            return {
                "mode": "single", 
                "strategy": self.single_manager.get_current_strategy_info()
            }
        return {"mode": "none"}
    
