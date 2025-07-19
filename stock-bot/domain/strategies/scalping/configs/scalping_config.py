from dataclasses import dataclass, field
from typing import Dict, Any
from domain.analysis.base.models import StrategyConfig
from domain.analysis.base.models.enums import StrategyType


@dataclass
class ScalpingStrategyConfig(StrategyConfig):
    """
    스캘핑 전략 설정
    빠른 진입/청산을 위한 단기 전략
    """
    name: str = "스캘핑 전략"
    description: str = "빠른 진입/청산을 위한 단기 전략"
    strategy_type: StrategyType = StrategyType.SCALPING
    signal_threshold: float = 4.0  # 매우 낮은 임계값
    risk_per_trade: float = 0.01
    max_positions: int = 10  # 초단기 다중 포지션
    position_hold_hours: int = 4   # 4시간 보유
    stop_loss_percentage: float = 3.0  # 낮은 손절
    take_profit_percentage: float = 6.0  # 낮은 익절
    score_multiplier: float = 1.1  # 점수 조정
    long_term_bullish_multiplier: float = 1.0
    long_term_bearish_multiplier: float = 1.0
    vix_high_multiplier: float = 1.2  # VIX 25 초과 시 점수 배수
    vix_low_multiplier: float = 0.8   # VIX 15 미만 시 점수 배수
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'rsi': 4.0,
        'stoch': 4.0,
        'volume': 5.0,
        'macd': 3.0
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
            'vix_high_multiplier': self.vix_high_multiplier,
            'vix_low_multiplier': self.vix_low_multiplier,
            'detector_weights': self.detector_weights
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScalpingStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            name=data.get('name', "스캘핑 전략"),
            description=data.get('description', "빠른 진입/청산을 위한 단기 전략"),
            strategy_type=StrategyType(data.get('strategy_type', StrategyType.SCALPING.value)),
            signal_threshold=data.get('signal_threshold', 4.0),
            risk_per_trade=data.get('risk_per_trade', 0.01),
            max_positions=data.get('max_positions', 10),
            position_hold_hours=data.get('position_hold_hours', 4),
            stop_loss_percentage=data.get('stop_loss_percentage', 3.0),
            take_profit_percentage=data.get('take_profit_percentage', 6.0),
            score_multiplier=data.get('score_multiplier', 1.1),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.0),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.0),
            vix_high_multiplier=data.get('vix_high_multiplier', 1.2),
            vix_low_multiplier=data.get('vix_low_multiplier', 0.8),
            detector_weights=data.get('detector_weights', {
                'rsi': 4.0, 'stoch': 4.0, 'volume': 5.0, 'macd': 3.0
            })
        )