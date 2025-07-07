"""
모디파이어 (Modifier) 시스템

거시 경제 상황에 따라 전략의 파라미터를 동적으로 변경하는 규칙들을 구현합니다.
각 모디파이어는 특정 조건을 확인하고, 조건이 충족되면 컨텍스트를 수정합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

from .decision_context import DecisionContext
from domain.analysis.config.dynamic_strategies import (
    ModifierDefinition, ModifierActionType, ModifierCondition, ModifierAction
)
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


class ModifierFactory:
    """모디파이어 팩토리"""
    
    @staticmethod
    def create_modifier(name: str, definition: ModifierDefinition) -> BaseModifier:
        """모디파이어 생성"""
        # 현재는 모든 모디파이어가 거시 지표 기반이므로 MarketIndicatorModifier 사용
        # 향후 다른 타입의 모디파이어가 필요하면 여기서 분기 처리
        return MarketIndicatorModifier(name, definition)
    
    @staticmethod
    def create_modifiers_from_config(modifier_names: list, 
                                   modifier_definitions: Dict[str, ModifierDefinition]) -> list[BaseModifier]:
        """설정에서 모디파이어 목록 생성"""
        modifiers = []
        
        for name in modifier_names:
            definition = modifier_definitions.get(name)
            if definition:
                modifier = ModifierFactory.create_modifier(name, definition)
                modifiers.append(modifier)
            else:
                logger.warning(f"Modifier definition not found: {name}")
        
        # 우선순위 순으로 정렬
        modifiers.sort(key=lambda m: m.definition.priority)
        
        return modifiers


class ModifierEngine:
    """모디파이어 엔진 - 여러 모디파이어를 순서대로 적용"""
    
    def __init__(self, modifiers: list[BaseModifier]):
        self.modifiers = modifiers
    
    def apply_all(self, context: DecisionContext, historical_data: pd.DataFrame,
                  market_data: Dict[str, Any]) -> int:
        """모든 모디파이어를 순서대로 적용"""
        applied_count = 0
        
        context.log_decision("MODIFIER_ENGINE_START", f"Starting to apply {len(self.modifiers)} modifiers")
        
        for modifier in self.modifiers:
            try:
                # 이미 거부(veto)된 경우, 추가 거부 모디파이어만 처리
                if context.is_vetoed and modifier.definition.action.type not in [
                    ModifierActionType.VETO_BUY, ModifierActionType.VETO_SELL, ModifierActionType.VETO_ALL
                ]:
                    context.log_decision("MODIFIER_SKIPPED", f"Skipped {modifier.name} due to existing veto")
                    continue
                
                applied = modifier.process(context, historical_data, market_data)
                if applied:
                    applied_count += 1
                    
            except Exception as e:
                logger.error(f"Error applying modifier '{modifier.name}': {e}")
                context.log_decision("MODIFIER_ERROR", f"Error in {modifier.name}: {e}")
        
        context.log_decision("MODIFIER_ENGINE_COMPLETE", 
                           f"Applied {applied_count} out of {len(self.modifiers)} modifiers")
        
        return applied_count 