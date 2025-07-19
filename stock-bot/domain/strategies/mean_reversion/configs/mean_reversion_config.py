"""
mean_reversion 전략 config

- BB(볼린저밴드, mean_reversion), RSI, Stoch Detector 조합
- signal_threshold: 7.0 (표준)
- position_management: 최대 4개, 24시간 보유(단기)
- name/description: 한글/영문 병기
"""
from domain.analysis.base.models import StrategyType
from dataclasses import dataclass, field
from typing import Dict, Any

# Detector 가중치 상수
MEAN_REVERSION_BB_WEIGHT = 6.0
MEAN_REVERSION_RSI_WEIGHT = 4.0
MEAN_REVERSION_STOCH_WEIGHT = 3.0

@dataclass
class MeanReversionConfig:
    name: str
    description: str
    signal_threshold: float
    risk_per_trade: float
    implementation_class: str
    detectors: list = field(default_factory=list)
    market_filters: Dict[str, Any] = field(default_factory=dict)
    position_management: Dict[str, Any] = field(default_factory=dict)

MEAN_REVERSION_CONFIG = MeanReversionConfig(
    name="평균회귀 전략 (Mean Reversion)",
    description="과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략",
    signal_threshold=7.0,
    risk_per_trade=0.015,
    implementation_class="domain.strategies.mean_reversion.mean_reversion_strategy.MeanReversionStrategy",
    detectors=[
        {"detector_class": "MeanReversionBBSignalDetector", "weight": MEAN_REVERSION_BB_WEIGHT, "detector_type": "mean_reversion"},
        {"detector_class": "MeanReversionRSISignalDetector", "weight": MEAN_REVERSION_RSI_WEIGHT},
        {"detector_class": "MeanReversionStochSignalDetector", "weight": MEAN_REVERSION_STOCH_WEIGHT},
    ],
    market_filters={},
    position_management={
        "max_positions": 4,
        "position_timeout_hours": 24
    }
) 