"""
자동 전략 선택기 - 시장 조건에 따른 자동 전략 선택을 담당
"""

from typing import Optional, Tuple, Any, Callable, Dict
import pandas as pd

from domain.signals.models.enums import StrategyType
from infrastructure.db.models.enums import TrendType
from domain.strategies.base import BaseStrategy
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class AutoStrategySelector:
    """시장 조건에 따른 자동 전략 선택을 관리하는 클래스"""
    
    def __init__(self):
        self.auto_strategy_selection = False
        self.market_condition_detection = True
        
        # 전략 교체를 위한 콜백 함수들
        self._static_strategy_switcher: Optional[Callable[[StrategyType], bool]] = None
        self._dynamic_strategy_switcher: Optional[Callable[[str], bool]] = None
        self._current_strategy_getter: Optional[Callable[[], Optional[BaseStrategy]]] = None
        self._current_dynamic_strategy_getter: Optional[Callable[[], Optional[Any]]] = None
    
    def set_strategy_switchers(self,
                             static_switcher: Callable[[StrategyType], bool],
                             dynamic_switcher: Callable[[str], bool],
                             current_strategy_getter: Callable[[], Optional[BaseStrategy]],
                             current_dynamic_strategy_getter: Callable[[], Optional[Any]]):
        """전략 교체를 위한 콜백 함수들을 설정합니다."""
        self._static_strategy_switcher = static_switcher
        self._dynamic_strategy_switcher = dynamic_switcher
        self._current_strategy_getter = current_strategy_getter
        self._current_dynamic_strategy_getter = current_dynamic_strategy_getter
    
    def enable_auto_strategy_selection(self, enable: bool = True):
        """자동 전략 선택 활성화/비활성화"""
        self.auto_strategy_selection = enable
        status = "활성화" if enable else "비활성화"
        logger.info(f"자동 전략 선택 {status}")
    
    def enable_market_condition_detection(self, enable: bool = True):
        """시장 조건 감지 활성화/비활성화"""
        self.market_condition_detection = enable
        status = "활성화" if enable else "비활성화"
        logger.info(f"시장 조건 감지 {status}")
    
    def enable(self, is_enabled: bool = True):
        """자동 전략 선택 시스템 전체 활성화/비활성화"""
        self.auto_strategy_selection = is_enabled
        self.market_condition_detection = is_enabled
        status = "활성화" if is_enabled else "비활성화"
        logger.info(f"자동 전략 선택 시스템 {status}")
    
    def get_current_strategy_info(self) -> Optional[Dict[str, Any]]:
        """현재 자동 선택 설정 정보를 반환합니다."""
        return {
            "manager_type": self.__class__.__name__,
            "auto_selection_enabled": self.auto_strategy_selection,
            "market_detection_enabled": self.market_condition_detection,
            "is_active": self.auto_strategy_selection and self.market_condition_detection
        }
    
    def auto_select_strategy(self, market_trend: TrendType, df: pd.DataFrame):
        """시장 상황에 따라 자동으로 전략을 선택합니다."""
        if not self.auto_strategy_selection or not self.market_condition_detection:
            return

        # 1. 시장 상황 분석 및 전략 추천 받기
        recommended_strategy = self._get_recommended_strategy_for_market(market_trend)
        if not recommended_strategy:
            return

        # 2. 추천받은 전략으로 교체
        self._apply_recommended_strategy(recommended_strategy, market_trend)
    
    def _get_recommended_strategy_for_market(self, market_trend: TrendType) -> Optional[Tuple[Any, str]]:
        """시장 상황에 대한 추천 전략을 가져옵니다."""
        market_condition = market_trend.value  # 예: 'BULLISH'
        
        # StrategySelector의 전역 인스턴스 사용
        from domain.orchestration.selector import strategy_selector
        
        recommended_strategy = strategy_selector.get_recommended_strategy(market_condition)
        if not recommended_strategy:
            logger.warning(f"시장 상황 '{market_condition}'에 대한 추천 전략을 찾지 못했습니다.")
            return None
        
        return recommended_strategy
    
    def _apply_recommended_strategy(self, recommended_strategy: Tuple[Any, str], market_trend: TrendType):
        """추천받은 전략을 적용합니다."""
        strategy_id, strategy_class = recommended_strategy
        market_condition = market_trend.value

        try:
            if strategy_class == 'static':
                self._switch_to_static_if_different(strategy_id, market_condition)
            elif strategy_class == 'dynamic':
                self._switch_to_dynamic_if_different(strategy_id, market_condition)
        except Exception as e:
            logger.error(f"추천 전략({strategy_id})으로 교체 중 오류 발생: {e}")
    
    def _switch_to_static_if_different(self, strategy_id: StrategyType, market_condition: str):
        """현재 전략과 다른 경우에만 정적 전략으로 교체합니다."""
        if not self._static_strategy_switcher or not self._current_strategy_getter:
            logger.error("정적 전략 교체 콜백이 설정되지 않았습니다.")
            return
            
        current_strategy = self._current_strategy_getter()
        if current_strategy is None or current_strategy.strategy_type != strategy_id:
            if self._static_strategy_switcher(strategy_id):
                logger.info(f"시장 상황 '{market_condition}'에 따라 정적 전략 자동 선택: {strategy_id.value}")
    
    def _switch_to_dynamic_if_different(self, strategy_id: str, market_condition: str):
        """현재 전략과 다른 경우에만 동적 전략으로 교체합니다."""
        if not self._dynamic_strategy_switcher or not self._current_dynamic_strategy_getter:
            logger.error("동적 전략 교체 콜백이 설정되지 않았습니다.")
            return
            
        current_dynamic_strategy = self._current_dynamic_strategy_getter()
        if (current_dynamic_strategy is None or 
            current_dynamic_strategy.strategy_name != strategy_id):
            if self._dynamic_strategy_switcher(strategy_id):
                logger.info(f"시장 상황 '{market_condition}'에 따라 동적 전략 자동 선택: {strategy_id}")
    
    @property
    def is_auto_selection_enabled(self) -> bool:
        """자동 전략 선택이 활성화되어 있는지 확인합니다."""
        return self.auto_strategy_selection
    
    @property
    def is_market_detection_enabled(self) -> bool:
        """시장 조건 감지가 활성화되어 있는지 확인합니다."""
        return self.market_condition_detection