from dataclasses import dataclass
from typing import Dict, Any
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType

@dataclass
class ScalpingStrategyConfig(StrategyConfig):
    """스캘핑 전략 설정"""
    strategy_type: StrategyType = StrategyType.SCALPING
    signal_threshold: float = 4.0  # 매우 낮은 임계값
    max_positions: int = 10  # 초단기 다중 포지션
    position_hold_hours: int = 4   # 4시간 보유
    risk_per_trade: float = 0.01
    vix_high_multiplier: float = 1.2  # VIX 25 초과 시 점수 배수
    vix_low_multiplier: float = 0.8   # VIX 15 미만 시 점수 배수
    detector_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.detector_weights is None:
            self.detector_weights = {
                'rsi': 4.0,
                'stoch': 4.0,
                'volume': 5.0,
                'macd': 3.0
            } 