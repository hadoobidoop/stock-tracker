# domain/analysis/strategy/dynamic_strategy_manager.py
from typing import Dict, List, Optional, Any

from .dynamic_strategy import DynamicCompositeStrategy
from .strategy_factory import StrategyFactory
from ..config.dynamic_strategies import get_all_strategies
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DynamicStrategyManager:
    """동적 전략(DynamicCompositeStrategy)의 생성, 관리, 실행을 전담하는 클래스"""

    def __init__(self):
        self.strategies: Dict[str, DynamicCompositeStrategy] = {}
        self.current_strategy: Optional[DynamicCompositeStrategy] = None
        self.is_enabled = True

    def initialize(self) -> int:
        """설정에 정의된 모든 동적 전략을 초기화합니다."""
        if not self.is_enabled:
            logger.info("Dynamic strategies are disabled. Skipping initialization.")
            return 0
            
        logger.info("Initializing dynamic strategies...")
        definitions = get_all_strategies()
        success_count = 0

        for name in definitions.keys():
            try:
                strategy = StrategyFactory.create_dynamic_strategy(name)
                if strategy and strategy.initialize():
                    self.strategies[name] = strategy
                    success_count += 1
                    logger.info(f"Dynamic strategy '{name}' initialized successfully.")
                else:
                    logger.error(f"Failed to initialize dynamic strategy: {name}")
            except Exception as e:
                logger.error(f"Exception during dynamic strategy initialization for '{name}': {e}", exc_info=True)
        
        self._set_default_strategy()
        logger.info(f"Initialized {success_count}/{len(definitions)} dynamic strategies.")
        return success_count

    def _set_default_strategy(self):
        """기본 동적 전략을 설정합니다."""
        if "dynamic_weight_strategy" in self.strategies:
            self.current_strategy = self.strategies["dynamic_weight_strategy"]
        elif self.strategies:
            self.current_strategy = next(iter(self.strategies.values()))
        
        if self.current_strategy:
            logger.info(f"Default dynamic strategy set to: {self.current_strategy.strategy_name}")

    def switch_strategy(self, name: str) -> bool:
        """활성 동적 전략을 교체합니��."""
        if name not in self.strategies:
            logger.warning(f"Dynamic strategy '{name}' not found.")
            return False
        
        self.current_strategy = self.strategies[name]
        logger.info(f"Switched to dynamic strategy: {name}")
        return True

    def get_strategy_info(self, name: str = None) -> Optional[Dict[str, Any]]:
        """특정 또는 현재 동적 전략의 정보를 반환합니다."""
        strategy = self.strategies.get(name) if name else self.current_strategy
        if not strategy:
            return None
            
        info = {
            "strategy_name": strategy.strategy_name,
            "description": strategy.strategy_config.get("description", ""),
            "signal_threshold": strategy.strategy_config.get("signal_threshold", 0),
            "risk_per_trade": strategy.strategy_config.get("risk_per_trade", 0),
            "detectors": strategy.strategy_config.get("detectors", {}),
            "modifiers": strategy.strategy_config.get("modifiers", []),
            "modifier_count": len(strategy.modifier_engine.modifiers) if strategy.modifier_engine else 0,
            "is_current": strategy == self.current_strategy
        }
        
        if strategy.last_context:
            info["last_analysis"] = strategy.get_context_summary()
        return info

    def get_detailed_log(self, name: str = None) -> List[Dict[str, Any]]:
        """특정 또는 현재 동적 전략의 상세 분석 로그를 반환합니다."""
        strategy = self.strategies.get(name) if name else self.current_strategy
        return strategy.get_detailed_log() if strategy else []

    def list_strategies(self) -> List[str]:
        """사용 가능한 모든 동적 전략의 이름을 반환합니다."""
        return list(self.strategies.keys())

    def enable(self, is_enabled: bool = True):
        """동적 전략 시스템을 활성화/비활성화합니다."""
        self.is_enabled = is_enabled
        logger.info(f"Dynamic strategy system has been {'enabled' if is_enabled else 'disabled'}.")
        if is_enabled and not self.strategies:
            self.initialize()
