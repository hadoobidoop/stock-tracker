from dataclasses import dataclass, field
from typing import Dict, Any

from domain.strategies.strategy_config import StrategyConfig
from domain.analysis.base.models.enums import StrategyType


@dataclass
class ConservativeReversionHybridConfig(StrategyConfig):
    """
    보수적 평균 회귀 하이브리드 전략 설정
    - 보수적 추세 확인 후 평균 회귀로 진입하는 전략
    - 안전성을 우선시하면서도 평균 회귀 기회를 포착
    - 낮은 리스크 설정으로 안정적인 수익 추구
    
    주요 특징:
        - name: 전략 이름(설명용)
        - description: 전략 설명(문서/로그용)  
        - signal_threshold: 신호 발생 기준점(기본 6.0)
        - risk_per_trade: 트레이드당 리스크 비율(0.015=1.5%)
        - detector_weights: 각 Detector별 가중치(평균회귀 지표 중심)
        - market_filters: 시장 필터링 설정(빈 딕셔너리)
        - position_management: 포지션 관리 설정(빈 딕셔너리)
    """
    name: str = "보수적 평균 회귀 하이브리드"
    description: str = "보수적 추세 확인 후 평균 회귀로 진입하는 전략"
    signal_threshold: float = 6.0  # 임계값을 약간 낮춰 더 많은 기회 포착
    risk_per_trade: float = 0.015  # 트레이드당 리스크 비율(1.5%)
    strategy_type: StrategyType = StrategyType.CONSERVATIVE_REVERSION_HYBRID  # 전략 유형(고정)
    max_positions: int = 3  # 최대 동시 포지션 수(보수적)
    position_hold_hours: int = 72  # 포지션 보유 시간(3일)
    stop_loss_percentage: float = 4.0  # 손절 기준(4% - 보수적)
    take_profit_percentage: float = 10.0  # 익절 기준(10% - 보수적)
    score_multiplier: float = 0.9  # 점수 조정 계수(보수적 접근)
    long_term_bullish_multiplier: float = 1.1  # 장기 상승장 가중치(보수적)
    long_term_bearish_multiplier: float = 1.2  # 장기 하락장 가중치(평균회귀 기회)
    detector_weights: Dict[str, float] = field(default_factory=lambda: {
        'bb': 6.0,  # 볼린저 밴드 중요도 높음
        'rsi': 5.0,  # RSI 과매수/과매도 지표
        'stoch': 4.0,  # 스토캐스틱 평균회귀
        'sma': 5.0,  # 이동평균 추세 확인
        'macd': 4.0,  # MACD 추세 전환
        'volume': 3.0,  # 거래량 확인
        'adx': 3.0   # 추세 강도 확인
    })  # Detector별 가중치(평균회귀 중심)
    
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
    def from_dict(cls, data: Dict[str, Any]) -> 'ConservativeReversionHybridConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            name=data.get('name', "보수적 평균 회귀 하이브리드"),
            description=data.get('description', "보수적 추세 확인 후 평균 회귀로 진입하는 전략"),
            strategy_type=StrategyType(data.get('strategy_type', StrategyType.CONSERVATIVE_REVERSION_HYBRID.value)),
            signal_threshold=data.get('signal_threshold', 6.0),
            risk_per_trade=data.get('risk_per_trade', 0.015),
            max_positions=data.get('max_positions', 3),
            position_hold_hours=data.get('position_hold_hours', 72),
            stop_loss_percentage=data.get('stop_loss_percentage', 4.0),
            take_profit_percentage=data.get('take_profit_percentage', 10.0),
            score_multiplier=data.get('score_multiplier', 0.9),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.1),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.2),
            detector_weights=data.get('detector_weights', {
                'bb': 6.0, 'rsi': 5.0, 'stoch': 4.0,
                'sma': 5.0, 'macd': 4.0, 'volume': 3.0, 'adx': 3.0
            })
        )