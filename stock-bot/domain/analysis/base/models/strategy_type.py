"""
전략 타입 정의
"""

from enum import Enum


class StrategyType(Enum):
    """전략 타입 정의 (확장 버전)"""
    # 기본 3가지 전략
    CONSERVATIVE = "conservative"    # 보수적 전략
    BALANCED = "balanced"           # 균형잡힌 전략 (기본)
    AGGRESSIVE = "aggressive"       # 공격적 전략
    
    # 확장 정적 전략들 (기존 시스템에서 이식)
    MOMENTUM = "momentum"           # 모멘텀 전략
    TREND_FOLLOWING = "trend_following"  # 추세추종 전략
    SCALPING = "scalping"           # 스캘핑 전략
    SWING = "swing"
    MEAN_REVERSION = "mean_reversion"
    TREND_PULLBACK = "trend_pullback"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    MULTI_TIMEFRAME = "multi_timeframe"
    ADAPTIVE_MOMENTUM = "adaptive_momentum"
    CONSERVATIVE_REVERSION_HYBRID = "conservative_reversion_hybrid"
    MARKET_REGIME_HYBRID = "market_regime_hybrid"
    MACRO_DRIVEN = "macro_driven"  # 동적 전략 시스템 전용 타입 (독립 전략 아님)
    DYNAMIC_WEIGHT = "dynamic_weight" # 동적 전략을 위한 플레이스홀더