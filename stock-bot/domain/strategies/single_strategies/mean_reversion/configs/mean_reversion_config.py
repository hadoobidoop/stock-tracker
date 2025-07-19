from dataclasses import dataclass, field
from typing import Dict, Any

from domain.strategies.strategy_config import StrategyConfig
from domain.analysis.models.enums import StrategyType


@dataclass
class MeanReversionStrategyConfig(StrategyConfig):
    """
    평균 회귀 전략 설정
    과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략
    """
    name: str = "평균 회귀 전략"
    description: str = "과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략"
    strategy_type: StrategyType = StrategyType.MEAN_REVERSION
    signal_threshold: float = 7.0
    risk_per_trade: float = 0.015
    max_positions: int = 4
    position_hold_hours: int = 24
    stop_loss_percentage: float = 4.0
    take_profit_percentage: float = 8.0
    score_multiplier: float = 1.0
    long_term_bullish_multiplier: float = 0.9  # 상승장에서는 평균회귀 기회 적음
    long_term_bearish_multiplier: float = 1.3  # 하락장에서는 평균회귀 기회 많음
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'bb': 6.0,      # 볼린저 밴드 - 평균회귀의 핵심
        'rsi': 4.0,     # RSI 과매수/과매도
        'stoch': 3.0    # 스토캐스틱 평균회귀
    })
    
    def __post_init__(self):
        pass  # detector_weights는 default_factory로 처리
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type.value,
            'signal_threshold': self.signal_threshold,
            'risk_per_trade': self.risk_per_trade,
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
    def from_dict(cls, data: Dict[str, Any]) -> 'MeanReversionStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            name=data.get('name', "평균 회귀 전략"),
            description=data.get('description', "과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략"),
            strategy_type=StrategyType(data.get('strategy_type', StrategyType.MEAN_REVERSION.value)),
            signal_threshold=data.get('signal_threshold', 7.0),
            risk_per_trade=data.get('risk_per_trade', 0.015),
            max_positions=data.get('max_positions', 4),
            position_hold_hours=data.get('position_hold_hours', 24),
            stop_loss_percentage=data.get('stop_loss_percentage', 4.0),
            take_profit_percentage=data.get('take_profit_percentage', 8.0),
            score_multiplier=data.get('score_multiplier', 1.0),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 0.9),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.3),
            detector_weights=data.get('detector_weights', {
                'bb': 6.0, 'rsi': 4.0, 'stoch': 3.0
            })
        )