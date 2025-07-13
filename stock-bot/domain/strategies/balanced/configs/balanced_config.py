from dataclasses import dataclass
from typing import Dict, Any
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType


@dataclass
class BalancedStrategyConfig(StrategyConfig):
    """균형 전략 설정"""
    
    # 기본 전략 설정 상속
    strategy_type: StrategyType = StrategyType.BALANCED
    signal_threshold: float = 8.0  # 기본값 유지
    max_positions: int = 4  # 기본값 유지
    position_hold_hours: int = 72  # 기본값 유지
    stop_loss_percentage: float = 5.0  # 기본값 유지
    take_profit_percentage: float = 12.0  # 기본값 유지
    
    # Balanced 전략 특화 설정
    score_multiplier: float = 1.0  # 점수 조정 없음 (균형)
    long_term_bullish_multiplier: float = 1.2  # 장기 상승장 배수
    long_term_bearish_multiplier: float = 1.2  # 장기 하락장 배수
    
    # Detector 가중치 (균형잡힌 설정)
    detector_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.detector_weights is None:
            self.detector_weights = {
                'sma': 5.0,
                'macd': 5.0,
                'rsi': 3.0,
                'volume': 4.0,
                'adx': 4.0,
                'composite': 7.0
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
    def from_dict(cls, data: Dict[str, Any]) -> 'BalancedStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 8.0),
            max_positions=data.get('max_positions', 4),
            position_hold_hours=data.get('position_hold_hours', 72),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 12.0),
            score_multiplier=data.get('score_multiplier', 1.0),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.2),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.2),
            detector_weights=data.get('detector_weights', {
                'sma': 5.0, 'macd': 5.0, 'rsi': 3.0, 
                'volume': 4.0, 'adx': 4.0, 'composite': 7.0
            })
        ) 