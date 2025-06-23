# ====================
# --- 전략별 설정 관리 ---
# ====================

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class StrategyType(Enum):
    """전략 타입 정의"""
    CONSERVATIVE = "conservative"    # 보수적 전략
    BALANCED = "balanced"           # 균형잡힌 전략 (기본)
    AGGRESSIVE = "aggressive"       # 공격적 전략
    MOMENTUM = "momentum"           # 모멘텀 전략
    TREND_FOLLOWING = "trend_following"  # 추세추종 전략
    CONTRARIAN = "contrarian"       # 역추세 전략
    SCALPING = "scalping"           # 스캘핑 전략
    SWING = "swing"                 # 스윙 전략

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
# --- 전략별 설정 정의 ---
# ====================

STRATEGY_CONFIGS = {
    StrategyType.CONSERVATIVE: StrategyConfig(
        name="보수적 전략",
        description="높은 신뢰도의 강한 신호만 사용하는 안전한 전략",
        signal_threshold=12.0,  # 높은 임계값
        risk_per_trade=0.01,    # 1% 리스크
        detectors=[
            DetectorConfig("SMASignalDetector", weight=7.5),  # 가중치 1.5배
            DetectorConfig("MACDSignalDetector", weight=7.5),
            DetectorConfig("VolumeSignalDetector", weight=6.0),
            # 복합 신호만 사용 (단일 신호는 제외)
            DetectorConfig("CompositeSignalDetector", weight=10.0, parameters={
                "require_all": True,
                "name": "MACD_Volume_Confirm",
                "sub_detectors": ["MACDSignalDetector", "VolumeSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": True,  # 시장 추세와 일치하는 신호만
            "volume_confirmation": True
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 72  # 3일
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
            }),
            DetectorConfig("CompositeSignalDetector", weight=6.0, parameters={
                "require_all": False,
                "name": "RSI_Stoch_Confirm",
                "sub_detectors": ["RSISignalDetector", "StochSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 5,
            "position_timeout_hours": 48  # 2일
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
            DetectorConfig("ADXSignalDetector", weight=3.0),
            # 개별 신호도 활용
            DetectorConfig("CompositeSignalDetector", weight=5.0, parameters={
                "require_all": False,  # OR 조건
                "name": "Any_Momentum",
                "sub_detectors": ["RSISignalDetector", "StochSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": False,
            "volume_confirmation": False
        },
        position_management={
            "max_positions": 8,
            "position_timeout_hours": 24  # 1일
        }
    ),
    
    StrategyType.MOMENTUM: StrategyConfig(
        name="모멘텀 전략",
        description="RSI, 스토캐스틱 등 모멘텀 지표 중심 전략",
        signal_threshold=6.0,
        risk_per_trade=0.025,
        detectors=[
            DetectorConfig("RSISignalDetector", weight=6.0),  # 높은 가중치
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
            "position_timeout_hours": 36
        }
    ),
    
    StrategyType.TREND_FOLLOWING: StrategyConfig(
        name="추세추종 전략",
        description="SMA, MACD, ADX 등 추세 지표 중심 전략",
        signal_threshold=7.0,
        risk_per_trade=0.02,
        detectors=[
            DetectorConfig("SMASignalDetector", weight=7.0),  # 높은 가중치
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
            "position_timeout_hours": 60  # 더 긴 보유
        }
    ),
    
    StrategyType.SCALPING: StrategyConfig(
        name="스캘핑 전략",
        description="빠른 진입/청산을 위한 단기 전략",
        signal_threshold=4.0,   # 매우 낮은 임계값
        risk_per_trade=0.015,   # 낮은 리스크
        detectors=[
            DetectorConfig("RSISignalDetector", weight=4.0),
            DetectorConfig("StochSignalDetector", weight=4.0),
            DetectorConfig("VolumeSignalDetector", weight=5.0),  # 거래량 중요
            DetectorConfig("MACDSignalDetector", weight=3.0)
        ],
        market_filters={
            "volume_confirmation": True,
            "volatility_filter": True
        },
        position_management={
            "max_positions": 6,
            "position_timeout_hours": 4,  # 4시간 이내 청산
            "quick_profit_target": 0.5,   # 0.5% 익절
            "tight_stop_loss": 0.3        # 0.3% 손절
        }
    ),
    
    StrategyType.SWING: StrategyConfig(
        name="스윙 전략",
        description="며칠간 보유하는 중기 전략",
        signal_threshold=9.0,
        risk_per_trade=0.03,
        detectors=[
            DetectorConfig("SMASignalDetector", weight=6.0),
            DetectorConfig("MACDSignalDetector", weight=6.0),
            DetectorConfig("RSISignalDetector", weight=4.0),
            DetectorConfig("ADXSignalDetector", weight=5.0),
            DetectorConfig("VolumeSignalDetector", weight=4.0),
            DetectorConfig("CompositeSignalDetector", weight=8.0, parameters={
                "require_all": True,
                "name": "Multi_Confirm",
                "sub_detectors": ["SMASignalDetector", "MACDSignalDetector"]
            })
        ],
        market_filters={
            "trend_alignment": True,
            "support_resistance": True
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 168,  # 7일
            "profit_target": 3.0,           # 3% 익절
            "stop_loss": 1.5                # 1.5% 손절
        }
    )
}

# ====================
# --- 동적 전략 조합 설정 ---
# ====================

class StrategyMixMode(Enum):
    """전략 조합 모드"""
    SINGLE = "single"           # 단일 전략
    WEIGHTED = "weighted"       # 가중치 기반 조합
    VOTING = "voting"           # 투표 기반 조합
    ENSEMBLE = "ensemble"       # 앙상블 기법

@dataclass
class StrategyMixConfig:
    """전략 조합 설정"""
    mode: StrategyMixMode
    strategies: Dict[StrategyType, float]  # 전략 타입 -> 가중치
    threshold_adjustment: float = 1.0
    conflict_resolution: str = "weighted_average"  # weighted_average, highest_score, majority_vote

# 미리 정의된 전략 조합
STRATEGY_MIXES = {
    "balanced_mix": StrategyMixConfig(
        mode=StrategyMixMode.WEIGHTED,
        strategies={
            StrategyType.BALANCED: 0.4,
            StrategyType.MOMENTUM: 0.3,
            StrategyType.TREND_FOLLOWING: 0.3
        },
        threshold_adjustment=0.9
    ),
    
    "conservative_mix": StrategyMixConfig(
        mode=StrategyMixMode.VOTING,
        strategies={
            StrategyType.CONSERVATIVE: 0.5,
            StrategyType.TREND_FOLLOWING: 0.3,
            StrategyType.SWING: 0.2
        },
        threshold_adjustment=1.2
    ),
    
    "aggressive_mix": StrategyMixConfig(
        mode=StrategyMixMode.WEIGHTED,
        strategies={
            StrategyType.AGGRESSIVE: 0.4,
            StrategyType.MOMENTUM: 0.3,
            StrategyType.SCALPING: 0.3
        },
        threshold_adjustment=0.8
    )
}

# ====================
# --- 시장 상황별 전략 자동 선택 ---
# ====================

MARKET_CONDITION_STRATEGIES = {
    "BULL_MARKET": {
        "primary": StrategyType.MOMENTUM,
        "secondary": StrategyType.AGGRESSIVE,
        "fallback": StrategyType.BALANCED
    },
    "BEAR_MARKET": {
        "primary": StrategyType.CONSERVATIVE,
        "secondary": StrategyType.CONTRARIAN,
        "fallback": StrategyType.SWING
    },
    "SIDEWAYS_MARKET": {
        "primary": StrategyType.SCALPING,
        "secondary": StrategyType.SWING,
        "fallback": StrategyType.BALANCED
    },
    "HIGH_VOLATILITY": {
        "primary": StrategyType.SCALPING,
        "secondary": StrategyType.MOMENTUM,
        "fallback": StrategyType.CONSERVATIVE
    },
    "LOW_VOLATILITY": {
        "primary": StrategyType.SWING,
        "secondary": StrategyType.TREND_FOLLOWING,
        "fallback": StrategyType.BALANCED
    }
} 