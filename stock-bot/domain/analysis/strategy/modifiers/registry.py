# domain/analysis/strategy/modifiers/registry.py
from typing import Dict, Type
from .base import BaseModifier
from .market_indicator_modifier import MarketIndicatorModifier
from ...config.dynamic_strategies import ModifierDefinition
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModifierRegistry:
    """모디파이어 클래스를 등록하고 관리하는 레지스트리"""
    _modifiers: Dict[str, Type[BaseModifier]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(modifier_class: Type[BaseModifier]):
            cls._modifiers[name] = modifier_class
            logger.debug(f"Modifier '{name}' registered to {modifier_class.__name__}")
            return modifier_class
        return decorator

    @classmethod
    def get_modifier_class(cls, name: str) -> Type[BaseModifier]:
        modifier_class = cls._modifiers.get(name)
        if not modifier_class:
            # 기본 또는 폴백 모디파이어 클래스를 반환할 수도 있음
            logger.warning(f"Modifier class for '{name}' not found, falling back to MarketIndicatorModifier.")
            return MarketIndicatorModifier
        return modifier_class

# 기본 모디파이어 등록
# 현재는 모든 모디파이어가 동일한 로직을 사용하므로, 하나의 클래스만 등록합니다.
# 향후 다른 종류의 모디파이어가 추가되면 여기에 등록합니다.
ModifierRegistry.register("market_indicator_modifier")(MarketIndicatorModifier)


class ModifierFactory:
    """모디파이어 팩토리"""
    
    @staticmethod
    def create_modifier(name: str, definition: ModifierDefinition) -> BaseModifier:
        """모디파이어 생성"""
        # 레지스트리에서 적절한 모디파이어 클래스를 가져옵니다.
        # 현재는 모든 모디파이어가 MarketIndicatorModifier 로직을 따르므로,
        # definition에 명시된 detector_type에 따라 클래스를 분기할 필요가 없습니다.
        # 만약 detector_type별로 다른 클래스가 필요하다면 여기서 분기합니다.
        modifier_class = ModifierRegistry.get_modifier_class("market_indicator_modifier")
        return modifier_class(name, definition)
    
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
