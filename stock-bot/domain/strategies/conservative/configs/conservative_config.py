from dataclasses import dataclass
from typing import Dict, Any
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType


@dataclass
class ConservativeStrategyConfig(StrategyConfig):
    """보수적 전략 설정"""
    
    # 기본 전략 설정 상속
    strategy_type: StrategyType = StrategyType.CONSERVATIVE
    signal_threshold: float = 12.0  # 높은 임계값 (기본 8.0 → 12.0)
    max_positions: int = 2  # 적은 포지션 (기본 4 → 2)
    position_hold_hours: int = 120  # 긴 보유 기간 (기본 72 → 120)
    stop_loss_percentage: float = 5.0  # 기본값 유지
    take_profit_percentage: float = 12.0  # 기본값 유지
    
    # Conservative 전략 특화 설정
    score_multiplier: float = 0.8  # 점수 조정 (기본 × 0.8)
    long_term_bullish_multiplier: float = 1.1  # 장기 상승장 배수 (기본 1.2 → 1.1)
    long_term_bearish_multiplier: float = 1.1  # 장기 하락장 배수 (기본 1.2 → 1.1)
    
    # Detector 가중치 (보수적인 설정)
    detector_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.detector_weights is None:
            self.detector_weights = {
                'sma': 6.0,
                'macd': 6.0,
                'volume': 5.0,
                'composite': 8.0
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
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
    def from_dict(cls, data: Dict[str, Any]) -> 'ConservativeStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 12.0),
            max_positions=data.get('max_positions', 2),
            position_hold_hours=data.get('position_hold_hours', 120),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 12.0),
            score_multiplier=data.get('score_multiplier', 0.8),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.1),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.1),
            detector_weights=data.get('detector_weights', {
                'sma': 6.0, 'macd': 6.0, 'volume': 5.0, 'composite': 8.0
            })
        ) 