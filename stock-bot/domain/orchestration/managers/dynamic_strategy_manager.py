# domain/strategies/dynamic/dynamic_strategy_manager.py

from typing import Dict, List, Optional, Any

from domain.orchestration.managers.base_strategy_manager import BaseStrategyManager
from domain.strategies.dynamic.dynamic_strategy_manager import DynamicCompositeStrategy
from domain.strategies.dynamic.dynamic_strategy_manager.configs.dynamic_strategies import get_all_strategies
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DynamicStrategyManager(BaseStrategyManager[DynamicCompositeStrategy, str]):
    """
    동적 전략(DynamicCompositeStrategy)의 생성, 관리, 실행을 전담하는 매니저 클래스.
    - 동적 전략이란? 시장 환경, 거시지표, 실시간 데이터 등에 따라 가중치/구성/룰이 동적으로 변하는 전략을 의미.
    - 이 매니저는 설정(config)에 정의된 모든 동적 전략을 인스턴스화하고, 활성 전략을 관리하며,
      전략 전환, 정보 조회, 상세 로그 제공, 시스템 활성/비활성화 등 핵심 기능을 제공한다.
    - 정적 전략(고정 룰 기반)과 달리, 동적 전략은 실시간/백테스트/자동화 등에서 유연하게 활용된다.
    
    주요 속성:
        - strategies: {전략명: 전략 인스턴스} 딕셔너리
        - current_strategy: 현재 활성화된 동적 전략 인스턴스
        - is_enabled: 동적 전략 시스템 전체 활성화 여부
    """

    def __init__(self):
        """
        DynamicStrategyManager 생성자.
        """
        super().__init__()

    def _create_strategy(self, strategy_key: str) -> Optional[DynamicCompositeStrategy]:
        """동적 전략 생성"""
        from domain.orchestration.factory import StrategyFactory  # Local import to avoid circular dependency
        return StrategyFactory.create_dynamic_strategy(strategy_key)

    def _get_default_strategy_key(self) -> Optional[str]:
        """기본 동적 전략 키 반환"""
        return "dynamic_weight_strategy" if "dynamic_weight_strategy" in self.strategies else None

    def _get_strategy_display_name(self, strategy: DynamicCompositeStrategy) -> str:
        """동적 전략 표시명 반환"""
        return strategy.strategy_name

    def _validate_strategy(self, strategy: DynamicCompositeStrategy, strategy_key: str) -> bool:
        """동적 전략 검증"""
        return strategy and strategy.initialize()

    def _get_available_strategy_keys(self) -> List[str]:
        """사용 가능한 동적 전략 키 목록 반환"""
        definitions = get_all_strategies()  # config에서 모든 동적 전략 정의를 가져옴
        return list(definitions.keys())

    def initialize(self) -> int:
        """
        설정(config)에 정의된 모든 동적 전략을 인스턴스화 및 초기화한다.
        하위 호환성을 위해 기존 메서드명 유지
        """
        return self.initialize_strategies()

    def get_strategy_info(self, name: str = None) -> Optional[Dict[str, Any]]:
        """
        특정 또는 현재 동적 전략의 상세 정보를 반환한다.
        Args:
            name (str, optional): 조회할 전략명. None이면 현재 활성 전략.
        Returns:
            dict or None: 전략 정보(설명, 임계값, 리스크, detector/모디파이어 구성, 최근 분석 등)
        """
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
        
        # 최근 분석 컨텍스트 요약 포함(있을 경우)
        if strategy.last_context:
            info["last_analysis"] = strategy.last_context.get_summary()
        return info

    def get_detailed_log(self, name: str = None) -> List[Dict[str, Any]]:
        """
        특정 또는 현재 동적 전략의 상세 분석 로그(의사결정 과정, 모디파이어 적용 내역 등)를 반환한다.
        Args:
            name (str, optional): 조회할 전략명. None이면 현재 활성 전략.
        Returns:
            list: 분석 로그(딕셔너리 리스트)
        """
        strategy = self.strategies.get(name) if name else self.current_strategy
        if strategy and strategy.last_context:
            return strategy.last_context.get_detailed_log()
        return []
