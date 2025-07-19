"""
전략 및 탐지기 설정 모델
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
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


@dataclass
class DetectorConfig:
    """신호 탐지기 설정"""
    detector_class: str
    weight: float
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    description: str
    signal_threshold: float
    risk_per_trade: float
    implementation_class: Optional[str] = None  # 구현 클래스 경로
    detectors: List[DetectorConfig] = field(default_factory=list)  # 이제 선택 사항
    market_filters: Dict[str, Any] = field(default_factory=dict)
    position_management: Dict[str, Any] = field(default_factory=dict)