from typing import Dict, Optional

from domain.analysis.base.models import StrategyConfig
from domain.analysis.base.models.enums import StrategyType
from domain.strategies.dynamic_strategies.adaptive_momentum_hybrid.configs.adaptive_momentum_hybrid_config import \
    AdaptiveMomentumHybridConfig
from domain.strategies.single_strategies.aggressive.configs.aggressive_config import AggressiveStrategyConfig
from domain.strategies.single_strategies.balanced.configs.balanced_config import BalancedStrategyConfig
# Strategy-specific config imports
from domain.strategies.single_strategies.conservative.configs.conservative_config import ConservativeStrategyConfig
from domain.strategies.dynamic_strategies.conservative_reversion_hybrid.configs.conservative_reversion_hybrid_config import \
    ConservativeReversionHybridConfig
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.configs.dynamic_strategies import get_all_strategies, get_strategy_definition, \
    get_all_modifiers
# Import standardized config classes
from domain.strategies.single_strategies.mean_reversion.configs.mean_reversion_config import MeanReversionStrategyConfig
from domain.strategies.single_strategies.momentum.configs.momentum_config import MomentumStrategyConfig
from domain.strategies.single_strategies.scalping.configs.scalping_config import ScalpingStrategyConfig

# Removed dependency on static_strategies.py - now using individual config classes

# Import legacy constants for configs not yet standardized
try:
    from domain.strategies.single_strategies.swing.configs.swing_config import SWING_STRATEGY_CONFIG
except ImportError:
    SWING_STRATEGY_CONFIG = None
    
try:
    from domain.strategies.single_strategies.multi_timeframe.configs.multi_timeframe_config import MULTI_TIMEFRAME_CONFIG
except ImportError:
    MULTI_TIMEFRAME_CONFIG = None
    
try:
    from domain.strategies.single_strategies.trend_following.configs.trend_following_config import TREND_FOLLOWING_CONFIG
except ImportError:
    TREND_FOLLOWING_CONFIG = None
    
try:
    from domain.strategies.dynamic_strategies.market_regime_hybrid.configs.market_regime_hybrid_config import MARKET_REGIME_HYBRID_CONFIG
except ImportError:
    MARKET_REGIME_HYBRID_CONFIG = None
from domain.analysis.strategy.base_strategy import BaseStrategy
from domain.strategies.dynamic_strategies.conservative_reversion_hybrid.conservative_reversion_hybrid_strategy import ConservativeReversionHybridStrategy
from domain.strategies.dynamic_strategies.adaptive_momentum_hybrid.adaptive_momentum_hybrid_strategy import AdaptiveMomentumStrategy
from domain.strategies.dynamic_strategies.market_regime_hybrid.market_regime_hybrid_strategy import MarketRegimeHybridStrategy
from domain.strategies.single_strategies.aggressive.aggressive_strategy import AggressiveStrategy
from domain.strategies.single_strategies.balanced.balanced_strategy import BalancedStrategy
from domain.strategies.single_strategies.momentum.momentum_strategy import MomentumStrategy
from domain.strategies.single_strategies.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
from domain.strategies.single_strategies.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.single_strategies.scalping.scalping_strategy import ScalpingStrategy
from domain.strategies.single_strategies.swing.swing_strategy import SwingStrategy
from domain.strategies.single_strategies.trend_following.trend_following_strategy import TrendFollowingStrategy
from domain.strategies.single_strategies.trend_pullback.trend_pullback_strategy import TrendPullbackStrategy
from domain.strategies.single_strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy
from domain.strategies.single_strategies.multi_timeframe.multi_timeframe_strategy import MultiTimeframeStrategy
from .modifier_engine import ModifierEngine
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.dynamic_strategy import DynamicCompositeStrategy
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.modifiers.registry import ModifierFactory
from infrastructure.logging import get_logger

logger = get_logger(__name__)

# 전략 타입 ↔️ 전략 클래스 매핑 딕셔너리
STRATEGY_CLASS_MAP = {
    StrategyType.ADAPTIVE_MOMENTUM: AdaptiveMomentumStrategy,
    StrategyType.CONSERVATIVE_REVERSION_HYBRID: ConservativeReversionHybridStrategy,
    StrategyType.MARKET_REGIME_HYBRID: MarketRegimeHybridStrategy,
    StrategyType.AGGRESSIVE: AggressiveStrategy,
    StrategyType.BALANCED: BalancedStrategy,
    StrategyType.CONSERVATIVE: ConservativeStrategy,
    StrategyType.MOMENTUM: MomentumStrategy,
    StrategyType.SCALPING: ScalpingStrategy,
    StrategyType.SWING: SwingStrategy,
    StrategyType.TREND_FOLLOWING: TrendFollowingStrategy,
    StrategyType.TREND_PULLBACK: TrendPullbackStrategy,
    StrategyType.MEAN_REVERSION: MeanReversionStrategy,
    StrategyType.VOLATILITY_BREAKOUT: VolatilityBreakoutStrategy,
    StrategyType.MULTI_TIMEFRAME: MultiTimeframeStrategy,
    # MACRO_DRIVEN is used by dynamic strategy system only, not as independent strategy
}

def get_strategy_specific_config(strategy_type: StrategyType):
    """전략별 특정 config 인스턴스 생성"""
    # Standardized config classes
    standardized_configs = {
        StrategyType.CONSERVATIVE: ConservativeStrategyConfig,
        StrategyType.BALANCED: BalancedStrategyConfig,
        StrategyType.AGGRESSIVE: AggressiveStrategyConfig,
        StrategyType.MOMENTUM: MomentumStrategyConfig,
        StrategyType.MEAN_REVERSION: MeanReversionStrategyConfig,
        StrategyType.SCALPING: ScalpingStrategyConfig,
        StrategyType.ADAPTIVE_MOMENTUM: AdaptiveMomentumHybridConfig,
        StrategyType.CONSERVATIVE_REVERSION_HYBRID: ConservativeReversionHybridConfig,
    }
    
    # Legacy constants for configs not yet standardized
    legacy_configs = {
        StrategyType.SWING: SWING_STRATEGY_CONFIG,
        StrategyType.MULTI_TIMEFRAME: MULTI_TIMEFRAME_CONFIG,
        StrategyType.TREND_FOLLOWING: TREND_FOLLOWING_CONFIG,
        StrategyType.MARKET_REGIME_HYBRID: MARKET_REGIME_HYBRID_CONFIG,
    }
    
    # Try standardized configs first
    if strategy_type in standardized_configs:
        config_class = standardized_configs[strategy_type]
        try:
            return config_class()
        except Exception as e:
            logger.warning(f"Failed to create standardized config for {strategy_type}: {e}")
    
    # Fallback to legacy configs
    if strategy_type in legacy_configs:
        legacy_config = legacy_configs[strategy_type]
        if legacy_config is not None:
            return legacy_config
    
    # Create basic StrategyConfig for unsupported strategies
    logger.warning(f"No specific config found for {strategy_type}, creating basic StrategyConfig")
    return StrategyConfig(
        name=f"{strategy_type.value.title()} Strategy",
        description=f"Basic configuration for {strategy_type.value} strategy",
        signal_threshold=7.0,
        risk_per_trade=0.02
    )
    
    config_creator = config_map.get(strategy_type)
    if config_creator:
        return config_creator()
    return None

class StrategyFactory:
    """
    통합 전략 팩토리 - 모든 정적 전략과 동적 전략 지원
    """

    @classmethod
    def create_static_strategy(cls, strategy_type: StrategyType,
                               config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """정적 전략 인스턴스 생성"""
        if config is None:
            # 전략별 특정 config 우선 사용
            config = get_strategy_specific_config(strategy_type)

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
    def get_available_static_strategies(cls) -> list[StrategyType]:
        """사용 가능한 정적 전략 목록 반환"""
        return list(STRATEGY_CLASS_MAP.keys())

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
            if strategy_type in STRATEGY_CLASS_MAP:
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
