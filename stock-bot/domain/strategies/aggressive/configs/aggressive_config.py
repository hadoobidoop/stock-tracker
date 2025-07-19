from dataclasses import dataclass, field
from typing import Dict, Any
from domain.analysis.base.models import StrategyConfig, StrategyType


@dataclass
class AggressiveStrategyConfig(StrategyConfig):
    """
    공격적 전략 설정
    - 낮은 임계값, 높은 포지션 수, 빠른 진입/청산을 특징으로 함
    - Detector별 가중치, 점수 배수, 장기추세 가중치 등 세부 파라미터 조정 가능
    주요 필드:
        - name: 전략 이름(설명용)
        - description: 전략 설명(문서/로그용)
        - signal_threshold: 신호 발생 기준점(기본 5.0)
        - risk_per_trade: 트레이드당 리스크 비율(0.03=3%)
        - detector_weights: 각 Detector별 가중치
        - score_multiplier: 점수 조정(기본 1.2)
        - max_positions/position_hold_hours: 포지션 관리(8개/48시간)
        - long_term_bullish_multiplier: 장기 상승장 가중치(1.3)
        - long_term_bearish_multiplier: 장기 하락장 가중치(1.2)
        - stop_loss_percentage: 손절 비율(5%)
        - take_profit_percentage: 익절 비율(12%)
    """
    name: str  # 전략 이름(설명용)
    description: str  # 전략 설명(문서/로그용)
    signal_threshold: float  # 신호 발생 기준점(기본 5.0)
    risk_per_trade: float  # 트레이드당 리스크 비율(0.03=3%)
    strategy_type: StrategyType = StrategyType.AGGRESSIVE  # 전략 타입(고정)
    max_positions: int = 8  # 최대 동시 포지션 수
    position_hold_hours: int = 48  # 포지션 최대 보유 시간(시간 단위)
    stop_loss_percentage: float = 5.0  # 손절 비율(%)
    take_profit_percentage: float = 12.0  # 익절 비율(%)
    score_multiplier: float = 1.2  # 점수 조정 계수(기본 1.2)
    long_term_bullish_multiplier: float = 1.3  # 장기 상승장 가중치
    long_term_bearish_multiplier: float = 1.2  # 장기 하락장 가중치
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'sma': 4.0,
        'macd': 4.0,
        'rsi': 3.0,
        'stoch': 3.0,
        'volume': 3.0,
        'adx': 3.0
    })  # Detector별 가중치
    
    def __post_init__(self):
        pass  # detector_weights는 default_factory로 처리하므로 별도 초기화 불필요
    
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
    def from_dict(cls, data: Dict[str, Any]) -> 'AggressiveStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 5.0),
            max_positions=data.get('max_positions', 8),
            position_hold_hours=data.get('position_hold_hours', 48),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 12.0),
            score_multiplier=data.get('score_multiplier', 1.2),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.3),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.2),
            detector_weights=data.get('detector_weights', {
                'sma': 4.0, 'macd': 4.0, 'rsi': 3.0, 
                'stoch': 3.0, 'volume': 3.0, 'adx': 3.0
            })
        ) 