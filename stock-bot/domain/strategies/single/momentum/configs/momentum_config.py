from dataclasses import dataclass, field
from typing import Dict, Any

from domain.signals.models.enums import StrategyType
from domain.strategies.strategy_config import StrategyConfig

# Detector weights constant
MOMENTUM_DETECTOR_WEIGHTS = {
    'rsi': 6.0,
    'stoch': 5.0,
    'macd': 4.0,
    'volume': 3.0,
    'composite': 8.0
}

@dataclass
class MomentumStrategyConfig(StrategyConfig):
    """
    모멘텀 전략 설정
    - RSI, Stoch 등 모멘텀 지표 중심의 신호 감지
    - 주요 파라미터, 가중치, 임계값 등 관리

    주요 튜닝 포인트:
        - name: 전략 이름(설명용)
        - description: 전략 설명(문서/로그용)
        - signal_threshold: 신호 발생 기준점(기본 6.0)
        - risk_per_trade: 트레이드당 리스크 비율(0.025=2.5%)
        - detector_weights: 각 Detector별 가중치(RSI > Stoch > MACD > Volume > Composite)
        - score_multiplier: 점수 조정(기본 1.0)
        - max_positions/position_hold_hours: 포지션 관리(4개/24시간)
        - long_term_bullish_multiplier: 장기 상승장 가중치(1.15)
        - long_term_bearish_multiplier: 장기 하락장 가중치(0.9)
        - stop_loss_percentage: 손절 비율(5%)
        - take_profit_percentage: 익절 비율(10%)
    """
    name: str = "모멘텀 전략"  # 전략 이름(설명용)
    description: str = "RSI, Stoch 등 모멘텀 지표 중심의 신호 감지"  # 전략 설명(문서/로그용)
    signal_threshold: float = 6.0  # 신호 발생 기준점(기본 6.0)
    risk_per_trade: float = 0.025  # 트레이드당 리스크 비율(0.025=2.5%)
    strategy_type: StrategyType = StrategyType.MOMENTUM  # 전략 타입(고정)
    max_positions: int = 4  # 최대 동시 포지션 수
    position_hold_hours: int = 24  # 포지션 최대 보유 시간(시간 단위)
    stop_loss_percentage: float = 5.0  # 손절 비율(%)
    take_profit_percentage: float = 10.0  # 익절 비율(%)
    score_multiplier: float = 1.0  # 점수 조정 계수(기본 1.0)
    long_term_bullish_multiplier: float = 1.15  # 장기 상승장 가중치
    long_term_bearish_multiplier: float = 0.9  # 장기 하락장 가중치
    detector_weights: Dict[str, float] = field(default_factory=lambda: MOMENTUM_DETECTOR_WEIGHTS.copy())  # Detector별 가중치

    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_type': self.strategy_type.value,
            'signal_threshold': self.signal_threshold,
            'max_positions': self.max_positions,
            'position_hold_hours': self.position_hold_hours,
            'stop_loss_percentage': self.stop_loss_percentage,
            'take_profit_percentage': self.take_profit_percentage,
            'score_multiplier': self.score_multiplier,
            'long_term_bullish_multiplier': self.long_term_bullish_multiplier,
            'long_term_bearish_multiplier': self.long_term_bearish_multiplier,
            'detector_weights': self.detector_weights
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MomentumStrategyConfig':
        return cls(
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 6.0),
            max_positions=data.get('max_positions', 4),
            position_hold_hours=data.get('position_hold_hours', 24),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 10.0),
            score_multiplier=data.get('score_multiplier', 1.0),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.15),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 0.9),
            detector_weights=data.get('detector_weights', MOMENTUM_DETECTOR_WEIGHTS)
        ) 