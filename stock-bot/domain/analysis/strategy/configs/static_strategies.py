"""
정적 전략 설정 (확장된 버전)

기존 정적 전략들을 모두 유지하면서 동적 전략 시스템과 호환되도록 구성
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class StrategyType(Enum):
    """전략 타입 정의 (확장 버전)"""
    # 기본 3가지 전략
    BALANCED = "balanced"           # 균형잡힌 전략 (기본)
    AGGRESSIVE = "aggressive"       # 공격적 전략
    
    # 확장 정적 전략들 (기존 시스템에서 이식)
    MOMENTUM = "momentum"           # 모멘텀 전략
    TREND_FOLLOWING = "trend_following"  # 추세추종 전략
    SCALPING = "scalping"           # 스캘핑 전략
    SWING = "swing"
    MEAN_REVERSION = "mean_reversion"
    TREND_PULLBACK = "trend_pullback"
    MULTI_TIMEFRAME = "multi_timeframe"
    MACRO_DRIVEN = "macro_driven"
    ADAPTIVE_MOMENTUM = "adaptive_momentum"
    CONSERVATIVE_REVERSION_HYBRID = "conservative_reversion_hybrid"
    MARKET_REGIME_HYBRID = "market_regime_hybrid"
    STABLE_VALUE_HYBRID = "stable_value_hybrid"
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


# ====================
# --- 확장된 정적 전략 설정 ---
# ====================

STRATEGY_CONFIGS = {
    # === 기본 3가지 전략 ===
    StrategyType.BALANCED: StrategyConfig(
        name="균형잡힌 전략",
        description="다양한 신호를 균형있게 사용하는 기본 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.balanced_strategy.BalancedStrategy",
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 5,
            "position_timeout_hours": 504  # 21일
        }
    ),
    
    StrategyType.AGGRESSIVE: StrategyConfig(
        name="공격적 전략",
        description="낮은 임계값으로 많은 거래 기회를 포착하는 전략",
        signal_threshold=5.0,   # 낮은 임계값
        risk_per_trade=0.03,    # 3% 리스크
        implementation_class="domain.analysis.strategy.implementations.aggressive_strategy.AggressiveStrategy",
        market_filters={
            "trend_alignment": False,
            "volume_confirmation": False
        },
        position_management={
            "max_positions": 8,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    # === 확장 정적 전략들 ===
    StrategyType.MOMENTUM: StrategyConfig(
        name="모멘텀 전략",
        description="RSI, 스토캐스틱 등 모멘텀 지표 중심 전략",
        signal_threshold=6.0,
        risk_per_trade=0.025,
        implementation_class="domain.analysis.strategy.implementations.momentum_strategy.MomentumStrategy",
        market_filters={
            "momentum_confirmation": True
        },
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 336
        }
    ),
    
    StrategyType.TREND_FOLLOWING: StrategyConfig(
        name="추세추종 전략",
        description="SMA, MACD, ADX 등 추세 지표 중심 전략",
        signal_threshold=7.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.trend_following_strategy.TrendFollowingStrategy",
        market_filters={
            "trend_alignment": True,
            "trend_strength": True
        },
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 720
        }
    ),
    
    StrategyType.SCALPING: StrategyConfig(
        name="스캘핑 전략",
        description="빠른 진입/청산을 위한 단기 전략",
        signal_threshold=4.0,   # 매우 낮은 임계값
        risk_per_trade=0.01,    # 낮은 리스크
        implementation_class="domain.analysis.strategy.implementations.scalping_strategy.ScalpingStrategy",
        market_filters={
            "volume_confirmation": True,
            "volatility_filter": True
        },
        position_management={
            "max_positions": 10,
            "position_timeout_hours": 4   # 4시간만 보유
        }
    ),
    
    StrategyType.SWING: StrategyConfig(
        name="스윙 전략",
        description="중기 추세 변화를 포착하는 전략",
        signal_threshold=7.0,
        risk_per_trade=0.025,
        implementation_class="domain.analysis.strategy.implementations.swing_strategy.SwingStrategy",
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    StrategyType.MEAN_REVERSION: StrategyConfig(
        name="평균 회귀 전략",
        description="과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략",
        signal_threshold=7.0,
        risk_per_trade=0.015,
        implementation_class="domain.analysis.strategy.implementations.mean_reversion_strategy.MeanReversionStrategy",
        market_filters={"trend_alignment": False},
        position_management={"max_positions": 4, "position_timeout_hours": 120}
    ),
    
    StrategyType.TREND_PULLBACK: StrategyConfig(
        name="추세 추종 눌림목 전략",
        description="상승 추세 중 일시적 하락(눌림목) 시 매수하는 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.trend_pullback_strategy.TrendPullbackStrategy",
        market_filters={"trend_alignment": True},
        position_management={"max_positions": 4, "position_timeout_hours": 120}
    ),
    
    StrategyType.MULTI_TIMEFRAME: StrategyConfig(
        name="다중 시간대 확인 전략",
        description="장기 추세(일봉)와 단기(시간봉) 진입 신호를 함께 확인하는 전략",
        signal_threshold=9.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.multi_timeframe_strategy.MultiTimeframeStrategy",
        market_filters={"multi_timeframe_confirmation": True},
        position_management={"max_positions": 3, "position_timeout_hours": 504}
    ),
    
    StrategyType.MACRO_DRIVEN: StrategyConfig(
        name="거시지표 기반 전략",
        description="VIX와 버핏지수 등 거시경제 지표를 기술적 분석과 결합한 전략",
        signal_threshold=7.0,
        risk_per_trade=0.015,
        implementation_class="domain.analysis.strategy.implementations.macro_driven_strategy.MacroDrivenStrategy",
        market_filters={
            "macro_sentiment_filter": True,
            "macro_signal_threshold": 3.0,
            "vix_analysis_enabled": True,
            "buffett_analysis_enabled": True,
            "dynamic_risk_adjustment": True
        },
        position_management={
            "max_positions": 4, 
            "position_timeout_hours": 720,
            "stop_loss_percent": 0.05,
            "take_profit_percent": 0.12
        }
    ),

    StrategyType.ADAPTIVE_MOMENTUM: StrategyConfig(
        name="적응형 모멘텀",
        description="추세, 모멘텀, 변동성을 결합한 적응형 전략",
        signal_threshold=6.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.adaptive_momentum_hybrid_strategy.AdaptiveMomentumStrategy",
        market_filters={},
        position_management={}
    ),

    StrategyType.CONSERVATIVE_REVERSION_HYBRID: StrategyConfig(
        name="보수적 평균 회귀 하이브리드",
        description="보수적 추세 확인 후 평균 회귀로 진입하는 전략",
        signal_threshold=6.0, # 임계값을 약간 낮춰 더 많은 기회 포착
        risk_per_trade=0.015,
        implementation_class="domain.analysis.strategy.implementations.conservative_reversion_hybrid.ConservativeReversionHybridStrategy",
        market_filters={},
        position_management={}
    ),

    StrategyType.MARKET_REGIME_HYBRID: StrategyConfig(
        name="시장 체제 적응형 하이브리드",
        description="시장의 추세와 변동성을 진단하여 최적의 하위 전략을 동적으로 선택",
        signal_threshold=6.0, # 하위 전략의 임계값을 따르므로, 중간값으로 설정
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.market_regime_hybrid.MarketRegimeHybridStrategy",
        market_filters={},
        position_management={}
    ),

    StrategyType.STABLE_VALUE_HYBRID: StrategyConfig(
        name="안정 가치 하이브리드",
        description="안정적인 추세에서 눌림목을 공략하는 우량주 특화 전략",
        signal_threshold=8.0, # 눌림목 전략의 임계값을 따름
        risk_per_trade=0.015,
        implementation_class="domain.analysis.strategy.implementations.stable_value_hybrid.StableValueHybridStrategy",
        market_filters={},
        position_management={}
    )
}


# ====================
# --- 호환성 함수들 ---
# ====================

def get_strategy_config(strategy_type: StrategyType) -> StrategyConfig:
    """전략 설정 조회"""
    return STRATEGY_CONFIGS.get(strategy_type)


def get_all_strategy_types() -> List[StrategyType]:
    """모든 전략 타입 반환"""
    return list(StrategyType)


def get_static_strategy_types() -> List[StrategyType]:
    """정적 전략 타입들만 반환 (동적 전략 제외)"""
    return [st for st in StrategyType if st != StrategyType.DYNAMIC_WEIGHT]


def get_available_strategies() -> Dict[str, List[str]]:
    """사용 가능한 전략들을 카테고리별로 반환"""
    return {
        "basic": ["BALANCED", "AGGRESSIVE"],
        "momentum": ["MOMENTUM", "RSI_STOCH", "SCALPING"],
        "trend": ["TREND_FOLLOWING", "TREND_PULLBACK"],
        "reversion": ["MEAN_REVERSION", "SWING"],
        "advanced": ["MULTI_TIMEFRAME", "MACRO_DRIVEN"]
    }


def is_strategy_available(strategy_name: str) -> bool:
    """전략 사용 가능 여부 확인"""
    try:
        strategy_type = StrategyType(strategy_name.lower())
        return strategy_type in STRATEGY_CONFIGS
    except ValueError:
        return False 