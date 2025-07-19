# domain/strategies/dynamic/dynamic_strategy_manager.py

from typing import Dict, List, Optional, Any

from domain.strategies.dynamic_strategies.dynamic_strategy_manager.configs.dynamic_strategies import get_all_strategies
from infrastructure.logging import get_logger
from .dynamic_strategy import DynamicCompositeStrategy
from ...strategy_factory import StrategyFactory

logger = get_logger(__name__)


class DynamicStrategyManager:
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
        - strategies: 동적 전략 인스턴스들을 저장하는 딕셔너리
        - current_strategy: 현재 활성화된 동적 전략
        - is_enabled: 동적 전략 시스템 전체 활성화 여부
        """
        self.strategies: Dict[str, DynamicCompositeStrategy] = {}
        self.current_strategy: Optional[DynamicCompositeStrategy] = None
        self.is_enabled = True

    def initialize(self) -> int:
        """
        설정(config)에 정의된 모든 동적 전략을 인스턴스화 및 초기화한다.
        - 이미 활성화된 전략이 있으면 재초기화(덮어씀)
        - 성공적으로 초기화된 전략 개수를 반환
        - 예외 발생 시 로깅 및 무시(전체 시스템 중단 방지)
        Returns:
            int: 성공적으로 초기화된 전략 개수
        """
        if not self.is_enabled:
            logger.info("Dynamic strategies are disabled. Skipping initialization.")
            return 0
            
        logger.info("Initializing dynamic strategies...")
        definitions = get_all_strategies()  # config에서 모든 동적 전략 정의를 가져옴
        success_count = 0

        for name in definitions.keys():
            try:
                # StrategyFactory를 통해 동적 전략 인스턴스 생성
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
        """
        기본 동적 전략을 설정한다.
        - 우선순위: 'dynamic_weight_strategy'가 있으면 이를 기본값으로, 없으면 첫 번째 전략을 기본값으로 설정
        - 설정 후, 현재 전략명을 info 로그로 남김
        """
        if "dynamic_weight_strategy" in self.strategies:
            self.current_strategy = self.strategies["dynamic_weight_strategy"]
        elif self.strategies:
            self.current_strategy = next(iter(self.strategies.values()))
        
        if self.current_strategy:
            logger.info(f"Default dynamic strategy set to: {self.current_strategy.strategy_name}")

    def switch_strategy(self, name: str) -> bool:
        """
        활성 동적 전략을 교체한다.
        Args:
            name (str): 교체할 동적 전략명
        Returns:
            bool: 성공 여부 (전략명이 존재하지 않으면 False)
        """
        if name not in self.strategies:
            logger.warning(f"Dynamic strategy '{name}' not found.")
            return False
        
        self.current_strategy = self.strategies[name]
        logger.info(f"Switched to dynamic strategy: {name}")
        return True

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
            info["last_analysis"] = strategy.get_context_summary()
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
        return strategy.get_detailed_log() if strategy else []

    def list_strategies(self) -> List[str]:
        """
        사용 가능한 모든 동적 전략의 이름(키)을 리스트로 반환한다.
        Returns:
            list[str]: 전략명 리스트
        """
        return list(self.strategies.keys())

    def enable(self, is_enabled: bool = True):
        """
        동적 전략 시스템 전체를 활성화/비활성화한다.
        - 비활성화 시 initialize() 등 모든 동적 전략 관련 동작이 중단됨
        - 활성화 후 전략이 없으면 자동으로 initialize() 호출
        Args:
            is_enabled (bool): 활성화 여부
        """
        self.is_enabled = is_enabled
        logger.info(f"Dynamic strategy system has been {'enabled' if is_enabled else 'disabled'}.")
        if is_enabled and not self.strategies:
            self.initialize()
