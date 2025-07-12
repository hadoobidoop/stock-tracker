# domain/analysis/strategy/modifier_engine.py
from typing import Dict, Any
import pandas as pd

from .decision_context import DecisionContext
from .modifiers.base import BaseModifier
from ..config.dynamic_strategies import ModifierActionType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


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
