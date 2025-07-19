from dataclasses import dataclass, field
from typing import Dict, Any

from domain.strategies.strategy_config import StrategyConfig
from domain.signals.models.enums import StrategyType


@dataclass
class AdaptiveMomentumHybridConfig(StrategyConfig):
    """
    적응형 모멘텀 하이브리드 전략 설정
    - 추세, 모멘텀, 변동성을 결합한 적응형 전략
    - 시장 상황에 따라 다양한 기술적 지표를 조합하여 신호 생성
    - 중간 수준의 신호 임계값과 리스크 관리
    
    주요 특징:
        - name: 전략 이름(설명용)
        - description: 전략 설명(문서/로그용)
        - signal_threshold: 신호 발생 기준점(기본 6.0)
        - risk_per_trade: 트레이드당 리스크 비율(0.02=2%)
        - detector_weights: 각 Detector별 가중치(모멘텀과 추세 지표 중심)
        - market_filters: 시장 필터링 설정(빈 딕셔너리)
        - position_management: 포지션 관리 설정(빈 딕셔너리)
    """
    name: str = "적응형 모멘텀 하이브리드"
    description: str = "추세, 모멘텀, 변동성을 결합한 적응형 전략"
    signal_threshold: float = 6.0  # 신호 발생 기준점
    risk_per_trade: float = 0.02  # 트레이드당 리스크 비율(2%)
    strategy_type: StrategyType = StrategyType.ADAPTIVE_MOMENTUM  # 전략 유형(고정)
    max_positions: int = 4  # 최대 동시 포지션 수
    position_hold_hours: int = 168  # 포지션 보유 시간(7일)
    stop_loss_percentage: float = 5.0  # 손절 기준(5%)
    take_profit_percentage: float = 12.0  # 익절 기준(12%)
    score_multiplier: float = 1.0  # 점수 조정 계수
    long_term_bullish_multiplier: float = 1.2  # 장기 상승장 가중치
    long_term_bearish_multiplier: float = 1.1  # 장기 하락장 가중치
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'rsi': 5.0,
        'macd': 5.0,
        'stoch': 4.0,
        'sma': 4.0,
        'adx': 4.0,
        'volume': 3.0,
        'bb': 3.0
    })  # Detector별 가중치(모멘텀 중심)
    
    def __post_init__(self):
        pass  # detector_weights는 default_factory로 처리하므로 별도 초기화 불필요
    
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
    def from_dict(cls, data: Dict[str, Any]) -> 'AdaptiveMomentumHybridConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            name=data.get('name', "적응형 모멘텀 하이브리드"),
            description=data.get('description', "추세, 모멘텀, 변동성을 결합한 적응형 전략"),
            strategy_type=StrategyType(data.get('strategy_type', StrategyType.ADAPTIVE_MOMENTUM.value)),
            signal_threshold=data.get('signal_threshold', 6.0),
            risk_per_trade=data.get('risk_per_trade', 0.02),
            max_positions=data.get('max_positions', 4),
            position_hold_hours=data.get('position_hold_hours', 168),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 12.0),
            score_multiplier=data.get('score_multiplier', 1.0),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.2),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.1),
            detector_weights=data.get('detector_weights', {
                'rsi': 5.0, 'macd': 5.0, 'stoch': 4.0, 
                'sma': 4.0, 'adx': 4.0, 'volume': 3.0, 'bb': 3.0
            })
        )