# domain/analysis/strategy/modifiers/market_indicator_modifier.py
from typing import Dict, Any

import pandas as pd

from .base import BaseModifier
from ..decision_context import DecisionContext
from ...config.dynamic_strategies import ModifierDefinition, ModifierActionType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketIndicatorModifier(BaseModifier):
    """거시 지표 기반 모디파이어"""
    
    def __init__(self, name: str, definition: ModifierDefinition):
        super().__init__(definition)
        self.name = name
        self.detector_key = definition.detector
    
    def check_condition(self, context: DecisionContext, historical_data: pd.DataFrame,
                       market_data: Dict[str, Any]) -> bool:
        """거시 지표 조건 확인"""
        condition = self.definition.condition
        
        # 시장 데이터에서 해당 지표 값 조회
        indicator_value = market_data.get(self.detector_key)
        if indicator_value is None:
            logger.warning(f"Market indicator '{self.detector_key}' not found in market_data")
            return False
        
        # 조건 연산자에 따른 비교
        if condition.operator == ">":
            return indicator_value > condition.value
        elif condition.operator == "<":
            return indicator_value < condition.value
        elif condition.operator == ">=":
            return indicator_value >= condition.value
        elif condition.operator == "<=":
            return indicator_value <= condition.value
        elif condition.operator == "==":
            return indicator_value == condition.value
        elif condition.operator == "!=":
            return indicator_value != condition.value
        elif condition.operator == "is_above":
            # S&P 500 같은 경우, 현재가가 200일선 위에 있는지 확인
            reference_value = market_data.get(f"{self.detector_key}_reference")
            if reference_value is None:
                logger.warning(f"Reference value for '{self.detector_key}' not found")
                return False
            return indicator_value > reference_value
        elif condition.operator == "is_below":
            reference_value = market_data.get(f"{self.detector_key}_reference")
            if reference_value is None:
                logger.warning(f"Reference value for '{self.detector_key}' not found")
                return False
            return indicator_value < reference_value
        else:
            logger.warning(f"Unknown condition operator: {condition.operator}")
            return False
    
    def apply_action(self, context: DecisionContext, historical_data: pd.DataFrame,
                    market_data: Dict[str, Any]):
        """액션 적용"""
        action = self.definition.action
        
        if action.type == ModifierActionType.VETO_BUY:
            context.set_veto(ModifierActionType.VETO_BUY, action.reason, self.name)
            
        elif action.type == ModifierActionType.VETO_SELL:
            context.set_veto(ModifierActionType.VETO_SELL, action.reason, self.name)
            
        elif action.type == ModifierActionType.VETO_ALL:
            context.set_veto(ModifierActionType.VETO_ALL, action.reason, self.name)
            
        elif action.type == ModifierActionType.ADJUST_WEIGHTS:
            if action.adjustments:
                for detector_name, adjustment in action.adjustments.items():
                    context.adjust_weight(detector_name, adjustment, self.name, action.reason)
                    
        elif action.type == ModifierActionType.ADJUST_SCORE:
            if action.multiplier:
                context.apply_score_multiplier(action.multiplier, self.name, action.reason)
                
        elif action.type == ModifierActionType.ADJUST_THRESHOLD:
            if action.threshold_adjustment:
                context.adjust_threshold(action.threshold_adjustment, self.name, action.reason)
        
        else:
            logger.warning(f"Unknown action type: {action.type}")
