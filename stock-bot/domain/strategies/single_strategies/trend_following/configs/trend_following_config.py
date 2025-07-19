from dataclasses import dataclass, field
from typing import Dict

from domain.analysis.base.models import StrategyConfig, StrategyType

# Detector별 가중치
SMA_WEIGHT = 4.0
MACD_WEIGHT = 4.0
ADX_WEIGHT = 3.0
VOLUME_WEIGHT = 2.0

TREND_FOLLOWING_DETECTOR_WEIGHTS = {
    'sma': SMA_WEIGHT,
    'macd': MACD_WEIGHT,
    'adx': ADX_WEIGHT,
    'volume': VOLUME_WEIGHT
}

@dataclass 
class TrendFollowingStrategyConfig(StrategyConfig):
    """
    Trend Following 전략 설정
    - SMA, MACD, ADX 등 추세 지표 중심의 신호 감지
    """
    name: str = "추세 추종 전략"
    description: str = "SMA, MACD, ADX를 활용한 추세 추종 전략"
    signal_threshold: float = 7.0
    risk_per_trade: float = 0.02
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    detector_weights: Dict[str, float] = field(default_factory=lambda: TREND_FOLLOWING_DETECTOR_WEIGHTS.copy())

# 기본 config 인스턴스
TREND_FOLLOWING_CONFIG = TrendFollowingStrategyConfig() 