"""
정적 전략 설정 (확장된 버전)

기존 정적 전략들을 모두 유지하면서 동적 전략 시스템과 호환되도록 구성
"""

from typing import Dict, Any, List
from dataclasses import dataclass
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
    CONTRARIAN = "contrarian"       # 역추세 전략
    SCALPING = "scalping"           # 스캘핑 전략
    SWING = "swing"                 # 스윙 전략
    MEAN_REVERSION = "mean_reversion"             # 평균 회귀 전략
    TREND_PULLBACK = "trend_pullback"             # 추세 추종 눌림목 전략
    VOLATILITY_BREAKOUT = "volatility_breakout"   # 변동성 돌파 전략
    QUALITY_TREND = "quality_trend"               # 고신뢰도 복합 추세 전략
    MULTI_TIMEFRAME = "multi_timeframe"           # 다중 시간대 확인 전략
    MACRO_DRIVEN = "macro_driven"                 # 거시지표 기반 전략
    
    # 동적 전략용 (호환성)
    DYNAMIC_WEIGHT = "dynamic_weight"   # 동적 가중치 전략


@dataclass
class DetectorConfig:
    """감지기 설정"""
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
    detectors: List[DetectorConfig]
    market_filters: Dict[str, Any] = None
    position_management: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.market_filters is None:
            self.market_filters = {}
        if self.position_management is None:
            self.position_management = {}


# ====================
# --- 확장된 정적 전략 설정 ---
# ====================

STRATEGY_CONFIGS = {
    # === 기본 3가지 전략 ===
    StrategyType.CONSERVATIVE: StrategyConfig(
        name="보수적 전략",
        description="높은 신뢰도의 강한 신호만 사용하는 안전한 전략",
        signal_threshold=12.0,  # 높은 임계값
        risk_per_trade=0.01,    # 1% 리스크
        detectors=[
            DetectorConfig("SMASignalDetector", weight=7.5),
            DetectorConfig("MACDSignalDetector", weight=7.5),
            DetectorConfig("VolumeSignalDetector", weight=6.0),
            DetectorConfig("CompositeSignalDetector", weight=10.0, parameters={
                "require_all": True,
                "name": "MACD_Volume_Confirm",
                "sub_detectors": ["MACDSignalDetector", "VolumeSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": True,
            "volume_confirmation": True
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    StrategyType.BALANCED: StrategyConfig(
        name="균형잡힌 전략",
        description="다양한 신호를 균형있게 사용하는 기본 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        detectors=[
            DetectorConfig("SMASignalDetector", weight=5.0),
            DetectorConfig("MACDSignalDetector", weight=5.0),
            DetectorConfig("RSISignalDetector", weight=3.0),
            DetectorConfig("VolumeSignalDetector", weight=4.0),
            DetectorConfig("ADXSignalDetector", weight=4.0),
            DetectorConfig("CompositeSignalDetector", weight=7.0, parameters={
                "require_all": True,
                "name": "MACD_Volume_Confirm",
                "sub_detectors": ["MACDSignalDetector", "VolumeSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 5,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    StrategyType.AGGRESSIVE: StrategyConfig(
        name="공격적 전략",
        description="낮은 임계값으로 많은 거래 기회를 포착하는 전략",
        signal_threshold=5.0,   # 낮은 임계값
        risk_per_trade=0.03,    # 3% 리스크
        detectors=[
            DetectorConfig("SMASignalDetector", weight=4.0),
            DetectorConfig("MACDSignalDetector", weight=4.0),
            DetectorConfig("RSISignalDetector", weight=3.0),
            DetectorConfig("StochSignalDetector", weight=3.0),
            DetectorConfig("VolumeSignalDetector", weight=3.0),
            DetectorConfig("ADXSignalDetector", weight=3.0)
        ],
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
        detectors=[
            DetectorConfig("RSISignalDetector", weight=6.0),
            DetectorConfig("StochSignalDetector", weight=5.0),
            DetectorConfig("MACDSignalDetector", weight=4.0),
            DetectorConfig("VolumeSignalDetector", weight=3.0),
            DetectorConfig("CompositeSignalDetector", weight=8.0, parameters={
                "require_all": True,
                "name": "RSI_Stoch_Confirm",
                "sub_detectors": ["RSISignalDetector", "StochSignalDetector"]
            })
        ],
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
        detectors=[
            DetectorConfig("SMASignalDetector", weight=7.0),
            DetectorConfig("MACDSignalDetector", weight=6.0),
            DetectorConfig("ADXSignalDetector", weight=6.0),
            DetectorConfig("VolumeSignalDetector", weight=4.0),
            DetectorConfig("CompositeSignalDetector", weight=8.0, parameters={
                "require_all": True,
                "name": "MACD_Volume_Confirm",
                "sub_detectors": ["MACDSignalDetector", "VolumeSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": True,
            "trend_strength": True
        },
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 60
        }
    ),
    
    StrategyType.CONTRARIAN: StrategyConfig(
        name="역추세 전략",
        description="과매수/과매도 상황에서 반대 방향으로 진입하는 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        detectors=[
            DetectorConfig("RSISignalDetector", weight=6.0),
            DetectorConfig("StochSignalDetector", weight=5.0),
            DetectorConfig("BBSignalDetector", weight=4.0, parameters={"detector_type": "mean_reversion"}),
        ],
        market_filters={
            "trend_alignment": False,
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 48
        }
    ),
    
    StrategyType.SCALPING: StrategyConfig(
        name="스캘핑 전략",
        description="빠른 진입/청산을 위한 단기 전략",
        signal_threshold=4.0,   # 매우 낮은 임계값
        risk_per_trade=0.01,    # 낮은 리스크
        detectors=[
            DetectorConfig("RSISignalDetector", weight=4.0),
            DetectorConfig("StochSignalDetector", weight=4.0),
            DetectorConfig("VolumeSignalDetector", weight=5.0),  # 거래량 중시
            DetectorConfig("MACDSignalDetector", weight=3.0)
        ],
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
        detectors=[
            DetectorConfig("SMASignalDetector", weight=5.0),
            DetectorConfig("MACDSignalDetector", weight=6.0),
            DetectorConfig("RSISignalDetector", weight=4.0),
            DetectorConfig("ADXSignalDetector", weight=4.0)
        ],
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 168  # 7일
        }
    ),
    
    StrategyType.MEAN_REVERSION: StrategyConfig(
        name="평균 회귀 전략",
        description="과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략",
        signal_threshold=7.0,
        risk_per_trade=0.015,
        detectors=[
            DetectorConfig("BBSignalDetector", weight=6.0, parameters={"detector_type": "mean_reversion"}),
            DetectorConfig("RSISignalDetector", weight=4.0),
            DetectorConfig("StochSignalDetector", weight=3.0),
        ],
        market_filters={"trend_alignment": False},
        position_management={"max_positions": 4, "position_timeout_hours": 24}
    ),
    
    StrategyType.TREND_PULLBACK: StrategyConfig(
        name="추세 추종 눌림목 전략",
        description="상승 추세 중 일시적 하락(눌림목) 시 매수하는 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        detectors=[
            DetectorConfig("SMASignalDetector", weight=5.0),
            DetectorConfig("ADXSignalDetector", weight=4.0),
            DetectorConfig("RSISignalDetector", weight=6.0),
        ],
        market_filters={"trend_alignment": True},
        position_management={"max_positions": 4, "position_timeout_hours": 72}
    ),
    
    StrategyType.VOLATILITY_BREAKOUT: StrategyConfig(
        name="변동성 돌파 전략",
        description="변동성 응축 후 폭발하는 시점을 포착하는 전략",
        signal_threshold=6.0,
        risk_per_trade=0.025,
        detectors=[
            DetectorConfig("BBSignalDetector", weight=7.0, parameters={"detector_type": "breakout"}),
            DetectorConfig("ADXSignalDetector", weight=4.0),
            DetectorConfig("VolumeSignalDetector", weight=5.0),
        ],
        market_filters={"volume_confirmation": True},
        position_management={"max_positions": 3, "position_timeout_hours": 48}
    ),
    
    StrategyType.QUALITY_TREND: StrategyConfig(
        name="고신뢰도 복합 추세 전략",
        description="여러 추세 지표가 모두 동의할 때만 진입하는 보수적 추세 전략",
        signal_threshold=10.0,
        risk_per_trade=0.01,
        detectors=[
            DetectorConfig("CompositeSignalDetector", weight=10.0, parameters={
                "require_all": True,
                "name": "Quality_Trend_Confirm",
                "sub_detectors": ["SMASignalDetector", "MACDSignalDetector", "ADXSignalDetector"]
            })
        ],
        market_filters={"trend_alignment": True, "trend_strength": True},
        position_management={"max_positions": 2, "position_timeout_hours": 120}
    ),
    
    StrategyType.MULTI_TIMEFRAME: StrategyConfig(
        name="다중 시간대 확인 전략",
        description="장기 추세(일봉)와 단기(시간봉) 진입 신호를 함께 확인하는 전략",
        signal_threshold=9.0,
        risk_per_trade=0.02,
        detectors=[
            DetectorConfig("MACDSignalDetector", weight=5.0),
            DetectorConfig("StochSignalDetector", weight=5.0),
            DetectorConfig("RSISignalDetector", weight=4.0),
        ],
        market_filters={"multi_timeframe_confirmation": True},
        position_management={"max_positions": 3, "position_timeout_hours": 96}
    ),
    
    StrategyType.MACRO_DRIVEN: StrategyConfig(
        name="거시지표 기반 전략",
        description="VIX와 버핏지수 등 거시경제 지표를 기술적 분석과 결합한 전략",
        signal_threshold=7.0,
        risk_per_trade=0.015,
        detectors=[
            DetectorConfig("MACDSignalDetector", weight=4.0),
            DetectorConfig("RSISignalDetector", weight=3.0),
            DetectorConfig("StochSignalDetector", weight=3.0),
            DetectorConfig("VolumeSignalDetector", weight=2.0),
        ],
        market_filters={
            "macro_sentiment_filter": True,
            "macro_signal_threshold": 3.0,
            "vix_analysis_enabled": True,
            "buffett_analysis_enabled": True,
            "dynamic_risk_adjustment": True
        },
        position_management={
            "max_positions": 4, 
            "position_timeout_hours": 120,
            "stop_loss_percent": 0.05,
            "take_profit_percent": 0.12
        }
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
        "basic": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"],
        "momentum": ["MOMENTUM", "RSI_STOCH", "SCALPING"],
        "trend": ["TREND_FOLLOWING", "TREND_PULLBACK", "QUALITY_TREND"],
        "reversion": ["CONTRARIAN", "MEAN_REVERSION", "SWING"],
        "advanced": ["VOLATILITY_BREAKOUT", "MULTI_TIMEFRAME", "MACRO_DRIVEN"]
    }


def is_strategy_available(strategy_name: str) -> bool:
    """전략 사용 가능 여부 확인"""
    try:
        strategy_type = StrategyType(strategy_name.lower())
        return strategy_type in STRATEGY_CONFIGS
    except ValueError:
        return False 