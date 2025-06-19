from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from infrastructure.db.models.enums import TrendType, SignalType


@dataclass
class TradingSignal:
    """거래 신호 도메인 모델"""
    
    ticker: str
    signal_type: SignalType
    signal_score: int
    timestamp_utc: datetime
    current_price: float
    
    # 추세 정보
    market_trend: TrendType
    long_term_trend: Optional[TrendType] = None
    trend_ref_close: Optional[float] = None
    trend_ref_value: Optional[float] = None
    
    # 신호 상세 정보
    details: List[str] = field(default_factory=list)
    stop_loss_price: Optional[float] = None
    
    # 메타데이터
    signal_id: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.signal_id is None:
            self.signal_id = f"signal_{self.ticker}_{int(self.timestamp_utc.timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """도메인 모델을 딕셔너리로 변환합니다."""
        return {
            'signal_id': self.signal_id,
            'ticker': self.ticker,
            'signal_type': self.signal_type,
            'signal_score': self.signal_score,
            'timestamp_utc': self.timestamp_utc,
            'current_price': self.current_price,
            'market_trend': self.market_trend,
            'long_term_trend': self.long_term_trend,
            'trend_ref_close': self.trend_ref_close,
            'trend_ref_value': self.trend_ref_value,
            'details': self.details,
            'stop_loss_price': self.stop_loss_price
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """딕셔너리에서 도메인 모델을 생성합니다."""
        return cls(
            signal_id=data.get('signal_id'),
            ticker=data['ticker'],
            signal_type=data['signal_type'],
            signal_score=data['signal_score'],
            timestamp_utc=data['timestamp_utc'],
            current_price=data['current_price'],
            market_trend=data['market_trend'],
            long_term_trend=data.get('long_term_trend'),
            trend_ref_close=data.get('trend_ref_close'),
            trend_ref_value=data.get('trend_ref_value'),
            details=data.get('details', []),
            stop_loss_price=data.get('stop_loss_price')
        )
    
    def is_buy_signal(self) -> bool:
        """매수 신호인지 확인합니다."""
        return self.signal_type == SignalType.BUY
    
    def is_sell_signal(self) -> bool:
        """매도 신호인지 확인합니다."""
        return self.signal_type == SignalType.SELL
    
    def get_risk_reward_ratio(self) -> Optional[float]:
        """위험 대비 수익 비율을 계산합니다."""
        if self.stop_loss_price is None:
            return None
        
        if self.is_buy_signal():
            # 매수 신호: (목표가 - 현재가) / (현재가 - 손절가)
            # 목표가는 현재가의 2배로 가정
            target_price = self.current_price * 2
            return (target_price - self.current_price) / (self.current_price - self.stop_loss_price)
        else:
            # 매도 신호: (현재가 - 목표가) / (손절가 - 현재가)
            # 목표가는 현재가의 절반으로 가정
            target_price = self.current_price * 0.5
            return (self.current_price - target_price) / (self.stop_loss_price - self.current_price)
    
    def get_signal_strength(self) -> str:
        """신호 강도를 반환합니다."""
        if self.signal_score >= 15:
            return "STRONG"
        elif self.signal_score >= 10:
            return "MEDIUM"
        else:
            return "WEAK" 