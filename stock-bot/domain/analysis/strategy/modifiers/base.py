# domain/analysis/strategy/modifiers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

from ..decision_context import DecisionContext
from ...config.dynamic_strategies import ModifierDefinition
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BaseModifier(ABC):
    """모디파이어 기본 클래스"""
    
    def __init__(self, definition: ModifierDefinition):
        self.definition = definition
        self.name = ""  # 실제 모디파이어 이름은 하위 클래스에서 설정
        
    @abstractmethod
    def check_condition(self, context: DecisionContext, historical_data: pd.DataFrame, 
                       market_data: Dict[str, Any]) -> bool:
        """조건 확인"""
        pass
    
    @abstractmethod
    def apply_action(self, context: DecisionContext, historical_data: pd.DataFrame,
                    market_data: Dict[str, Any]):
        """액션 적용"""
        pass
    
    def process(self, context: DecisionContext, historical_data: pd.DataFrame,
                market_data: Dict[str, Any]) -> bool:
        """모디파이어 처리 (조건 확인 후 액션 적용)"""
        try:
            if not self.definition.enabled:
                context.record_modifier_application(
                    self.name, self.definition.action.type.value, False, "Modifier disabled"
                )
                return False
            
            # 조건 확인
            condition_met = self.check_condition(context, historical_data, market_data)
            
            if condition_met:
                # 액션 적용
                self.apply_action(context, historical_data, market_data)
                context.record_modifier_application(
                    self.name, self.definition.action.type.value, True,
                    self.definition.action.reason or self.definition.description
                )
                logger.info(f"Modifier '{self.name}' applied: {self.definition.action.reason}")
                return True
            else:
                context.record_modifier_application(
                    self.name, self.definition.action.type.value, False, "Condition not met"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error processing modifier '{self.name}': {e}")
            context.record_modifier_application(
                self.name, self.definition.action.type.value, False, f"Error: {e}"
            )
            return False
