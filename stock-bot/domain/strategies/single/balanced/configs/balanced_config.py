from dataclasses import dataclass, field
from typing import Dict, Any

from domain.signals.models.enums import StrategyType
from domain.strategies.strategy_config import StrategyConfig


@dataclass
class BalancedStrategyConfig(StrategyConfig):
    """
    균형 전략 설정
    - 신호 신뢰도와 빈도의 균형, 표준적/안정적 운용을 목표로 함
    - aggressive/conservative 대비 중립적 파라미터
    - Detector별 가중치, 임계값, 포지션 관리 등 주요 파라미터 일괄 관리

    주요 튜닝 포인트:
        - name: 전략 이름(설명용)
        - description: 전략 설명(문서/로그용)
        - signal_threshold: 신호 발생 기준점(기본 8.0)
        - risk_per_trade: 트레이드당 리스크 비율(0.02=2%)
        - detector_weights: 각 Detector별 가중치(Composite > SMA/MACD > Volume/ADX > RSI)
        - long_term_bullish_multiplier/long_term_bearish_multiplier: 장기추세 가중치(기본 1.2)
        - score_multiplier: 점수 조정(기본 1.0)
        - max_positions/position_hold_hours: 포지션 관리(5개/21일)
    """
    name: str = "균형잡힌 전략"  # 전략 이름(설명용)
    description: str = "다양한 신호를 균형있게 사용하는 기본 전략"  # 전략 설명(문서/로그용)
    signal_threshold: float = 8.0  # 신호 발생 기준점(기본 8.0)
    risk_per_trade: float = 0.02  # 트레이드당 리스크 비율(0.02=2%)
    strategy_type: StrategyType = StrategyType.BALANCED  # 전략 유형(고정)
    max_positions: int = 5  # 최대 동시 포지션(5개, static_strategies.py 기준)
    position_hold_hours: int = 504  # 포지션 보유 시간(21일, static_strategies.py 기준)
    stop_loss_percentage: float = 5.0  # 손절 기준(5%)
    take_profit_percentage: float = 12.0  # 익절 기준(12%)
    score_multiplier: float = 1.0  # 점수 조정 없음(1.0)
    long_term_bullish_multiplier: float = 1.2  # 장기 상승장 buy 가중치(1.2)
    long_term_bearish_multiplier: float = 1.2  # 장기 하락장 sell 가중치(1.2)
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'sma': 5.0,
        'macd': 5.0,
        'rsi': 3.0,
        'volume': 4.0,
        'adx': 4.0,
        'composite': 7.0
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
    def from_dict(cls, data: Dict[str, Any]) -> 'BalancedStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            name=data.get('name', "균형잡힌 전략"),
            description=data.get('description', "다양한 신호를 균형있게 사용하는 기본 전략"),
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 8.0),
            risk_per_trade=data.get('risk_per_trade', 0.02),
            max_positions=data.get('max_positions', 5),
            position_hold_hours=data.get('position_hold_hours', 504),
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