from typing import Dict, Optional

from domain.analysis.config.dynamic_strategies import get_all_strategies, get_strategy_definition
from domain.analysis.config.static_strategies import StrategyType, StrategyConfig, get_strategy_config, \
    get_static_strategy_types
from domain.analysis.strategy.base_strategy import BaseStrategy
from domain.analysis.strategy.implementations import (
    AdaptiveMomentumStrategy,
    ConservativeReversionHybridStrategy,
    MarketRegimeHybridStrategy,
    StableValueHybridStrategy,
    UniversalStrategy
)
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StrategyFactory:
    """
    통합 전략 팩토리 - 모든 정적 전략과 동적 전략 지원

    개선 사항:
    1. 모든 확장된 정적 전략 지원
    2. 동적 전략 생성 기능 추가
    3. 중복 경고 메시지 제거
    4. 설정 기반 전략 생성
    """

    @classmethod
    def create_static_strategy(cls, strategy_type: StrategyType,
                               config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """정적 전략 인스턴스 생성"""
        if config is None:
            config = get_strategy_config(strategy_type)

        if config is None:
            logger.error(f"전략 설정을 찾을 수 없습니다: {strategy_type.value}")
            return None

        try:
            if strategy_type == StrategyType.ADAPTIVE_MOMENTUM:
                return AdaptiveMomentumStrategy(strategy_type, config)
            if strategy_type == StrategyType.CONSERVATIVE_REVERSION_HYBRID:
                return ConservativeReversionHybridStrategy(strategy_type, config)
            if strategy_type == StrategyType.MARKET_REGIME_HYBRID:
                return MarketRegimeHybridStrategy(strategy_type, config)
            if strategy_type == StrategyType.STABLE_VALUE_HYBRID:
                return StableValueHybridStrategy(strategy_type, config)

            # 모든 나머지 정적 전략을 UniversalStrategy로 생성
            strategy = UniversalStrategy(strategy_type, config)
            logger.info(f"정적 전략 생성 성공: {strategy_type.value}")
            return strategy

        except Exception as e:
            logger.error(f"정적 전략 생성 실패 {strategy_type.value}: {e}")
            return None

    @classmethod
    def create_dynamic_strategy(cls, strategy_name: str) -> Optional[BaseStrategy]:
        """동적 전략 인스턴스 생성"""
        try:
            from .dynamic_strategy import DynamicCompositeStrategy
            strategy = DynamicCompositeStrategy(strategy_name)
            logger.info(f"동적 전략 생성 성공: {strategy_name}")
            return strategy

        except Exception as e:
            logger.error(f"동적 전략 생성 실패 {strategy_name}: {e}")
            return None

    @classmethod
    def create_strategy(cls, strategy_type: StrategyType,
                        config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """전략 인스턴스 생성 (하위 호환성 유지)"""
        return cls.create_static_strategy(strategy_type, config)

    @classmethod
    def get_available_static_strategies(self) -> list[StrategyType]:
        """사용 가능한 정적 전략 목록 반환"""
        return get_static_strategy_types()

    @classmethod
    def get_available_dynamic_strategies(self) -> list[str]:
        """사용 가능한 동적 전략 목록 반환"""
        try:
            return list(get_all_strategies().keys())
        except ImportError:
            return []

    @classmethod
    def is_strategy_supported(cls, strategy_identifier: str) -> tuple[bool, str]:
        """전략 지원 여부 확인"""
        # 정적 전략 확인
        try:
            strategy_type = StrategyType(strategy_identifier.lower())
            if get_strategy_config(strategy_type) is not None:
                return True, "static"
        except ValueError:
            pass

        # 동적 전략 확인
        try:
            if get_strategy_definition(strategy_identifier) is not None:
                return True, "dynamic"
        except ImportError:
            def get_strategy_definition(name):
                return None

            if get_strategy_definition(strategy_identifier) is not None:
                return True, "dynamic"

        return False, "none"

    @classmethod
    def create_multiple_strategies(cls,
                                   strategy_configs: Dict[StrategyType, StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """여러 정적 전략 동시 생성"""
        strategies = {}
        for strategy_type, config in strategy_configs.items():
            strategy = cls.create_static_strategy(strategy_type, config)
            if strategy:
                strategies[strategy_type] = strategy
            else:
                logger.warning(f"전략 생성 실패로 건너뜀: {strategy_type.value}")
        return strategies
