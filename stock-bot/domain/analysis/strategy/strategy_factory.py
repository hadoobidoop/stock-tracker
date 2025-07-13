from typing import Dict, Optional

from domain.analysis.config.dynamic_strategies import get_all_strategies, get_strategy_definition, get_all_modifiers
from domain.analysis.config.static_strategies import StrategyType, StrategyConfig, get_strategy_config, \
    get_static_strategy_types
from domain.analysis.strategy.base_strategy import BaseStrategy
from domain.analysis.strategy.implementations import (
    AdaptiveMomentumStrategy,
    ConservativeReversionHybridStrategy,
    MarketRegimeHybridStrategy,
    StableValueHybridStrategy,
    AggressiveStrategy,
    BalancedStrategy,
    ConservativeStrategy,
    ContrarianStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    ScalpingStrategy,
    SwingStrategy,
    TrendFollowingStrategy,
    TrendPullbackStrategy,
    VolatilityBreakoutStrategy
)
from .modifier_engine import ModifierEngine
from .modifiers.registry import ModifierFactory
from infrastructure.logging import get_logger

logger = get_logger(__name__)

# 전략 타입 ↔️ 전략 클래스 매핑 딕셔너리
STRATEGY_CLASS_MAP = {
    StrategyType.ADAPTIVE_MOMENTUM: AdaptiveMomentumStrategy,
    StrategyType.CONSERVATIVE_REVERSION_HYBRID: ConservativeReversionHybridStrategy,
    StrategyType.MARKET_REGIME_HYBRID: MarketRegimeHybridStrategy,
    StrategyType.STABLE_VALUE_HYBRID: StableValueHybridStrategy,
    StrategyType.AGGRESSIVE: AggressiveStrategy,
    StrategyType.BALANCED: BalancedStrategy,
    StrategyType.CONSERVATIVE: ConservativeStrategy,
    StrategyType.CONTRARIAN: ContrarianStrategy,
    StrategyType.MEAN_REVERSION: MeanReversionStrategy,
    StrategyType.MOMENTUM: MomentumStrategy,
    StrategyType.SCALPING: ScalpingStrategy,
    StrategyType.SWING: SwingStrategy,
    StrategyType.TREND_FOLLOWING: TrendFollowingStrategy,
    StrategyType.TREND_PULLBACK: TrendPullbackStrategy,
    StrategyType.VOLATILITY_BREAKOUT: VolatilityBreakoutStrategy,
}

class StrategyFactory:
    """
    통합 전략 팩토리 - 모든 정적 전략과 동적 전략 지원
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
            strategy_class = STRATEGY_CLASS_MAP.get(strategy_type)
            if strategy_class is None:
                logger.error(f"지원하지 않는 전략 타입입니다: {strategy_type.value}")
                return None
            return strategy_class(strategy_type, config)
        except Exception as e:
            logger.error(f"정적 전략 생성 실패 {strategy_type.value}: {e}")
            return None

    @classmethod
    def create_dynamic_strategy(cls, strategy_name: str) -> Optional[BaseStrategy]:
        """동적 전략 인스턴스 생성 및 의존성 주입"""
        try:
            from .dynamic_strategy import DynamicCompositeStrategy
            
            strategy_config = get_strategy_definition(strategy_name)
            if not strategy_config:
                logger.error(f"Dynamic strategy definition not found: {strategy_name}")
                return None

            # 1. ModifierEngine 생성
            modifier_definitions = get_all_modifiers()
            modifier_names = strategy_config.get("modifiers", [])
            modifiers = ModifierFactory.create_modifiers_from_config(modifier_names, modifier_definitions)
            modifier_engine = ModifierEngine(modifiers)

            # 2. DynamicCompositeStrategy에 의존성 주입
            strategy = DynamicCompositeStrategy(
                strategy_name=strategy_name,
                strategy_config=strategy_config,
                modifier_engine=modifier_engine
            )

            # 3. 전략 초기화
            if not strategy.initialize():
                logger.error(f"Failed to initialize dynamic strategy: {strategy_name}")
                return None

            logger.info(f"동적 전략 생성 및 초기화 성공: {strategy_name}")
            return strategy

        except Exception as e:
            logger.error(f"동적 전략 생성 실패 {strategy_name}: {e}", exc_info=True)
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
