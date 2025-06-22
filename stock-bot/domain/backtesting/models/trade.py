from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class TradeType(Enum):
    """거래 유형"""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(Enum):
    """거래 상태"""
    OPEN = "OPEN"           # 진행중
    CLOSED = "CLOSED"       # 완료
    STOP_LOSS = "STOP_LOSS" # 손절
    TAKE_PROFIT = "TAKE_PROFIT"  # 익절


@dataclass
class Trade:
    """거래 도메인 모델"""
    
    # 기본 정보
    trade_id: str
    ticker: str
    trade_type: TradeType
    status: TradeStatus
    
    # 진입 정보
    entry_timestamp: datetime
    entry_price: float
    entry_quantity: int
    entry_signal_details: List[str]
    entry_signal_score: int
    
    # 청산 정보 (선택적)
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_signal_details: Optional[List[str]] = None
    exit_signal_score: Optional[int] = None
    
    # 손절/익절 설정
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # 수익률 정보
    pnl: Optional[float] = None  # 손익 (절대값)
    pnl_percent: Optional[float] = None  # 수익률 (%)
    
    # 거래 기간
    holding_period_hours: Optional[float] = None
    
    # 시장 환경
    market_trend_at_entry: Optional[str] = None
    long_term_trend_at_entry: Optional[str] = None
    
    # 추가 메타데이터
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def calculate_pnl(self) -> None:
        """손익 계산"""
        if self.exit_price is None:
            return
            
        if self.trade_type == TradeType.BUY:
            self.pnl = (self.exit_price - self.entry_price) * self.entry_quantity
            self.pnl_percent = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SELL (공매도)
            self.pnl = (self.entry_price - self.exit_price) * self.entry_quantity
            self.pnl_percent = ((self.entry_price - self.exit_price) / self.entry_price) * 100
    
    def calculate_holding_period(self) -> None:
        """보유 기간 계산 (시간 단위)"""
        if self.exit_timestamp is None:
            return
        
        time_diff = self.exit_timestamp - self.entry_timestamp
        self.holding_period_hours = time_diff.total_seconds() / 3600
    
    def close_trade(self, 
                   exit_timestamp: datetime,
                   exit_price: float,
                   exit_signal_details: Optional[List[str]] = None,
                   exit_signal_score: Optional[int] = None,
                   status: TradeStatus = TradeStatus.CLOSED) -> None:
        """거래 청산"""
        self.exit_timestamp = exit_timestamp
        self.exit_price = exit_price
        self.exit_signal_details = exit_signal_details or []
        self.exit_signal_score = exit_signal_score
        self.status = status
        
        self.calculate_pnl()
        self.calculate_holding_period()
    
    def is_stop_loss_triggered(self, current_price: float) -> bool:
        """손절 조건 확인"""
        if self.stop_loss_price is None:
            return False
            
        if self.trade_type == TradeType.BUY:
            return current_price <= self.stop_loss_price
        else:  # SELL
            return current_price >= self.stop_loss_price
    
    def is_take_profit_triggered(self, current_price: float) -> bool:
        """익절 조건 확인"""
        if self.take_profit_price is None:
            return False
            
        if self.trade_type == TradeType.BUY:
            return current_price >= self.take_profit_price
        else:  # SELL
            return current_price <= self.take_profit_price
    
    def get_current_pnl(self, current_price: float) -> tuple[float, float]:
        """현재 가격 기준 미실현 손익 계산"""
        if self.trade_type == TradeType.BUY:
            pnl = (current_price - self.entry_price) * self.entry_quantity
            pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SELL
            pnl = (self.entry_price - current_price) * self.entry_quantity  
            pnl_percent = ((self.entry_price - current_price) / self.entry_price) * 100
            
        return pnl, pnl_percent
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'trade_id': self.trade_id,
            'ticker': self.ticker,
            'trade_type': self.trade_type.value,
            'status': self.status.value,
            'entry_timestamp': self.entry_timestamp.isoformat(),
            'entry_price': self.entry_price,
            'entry_quantity': self.entry_quantity,
            'entry_signal_details': self.entry_signal_details,
            'entry_signal_score': self.entry_signal_score,
            'exit_timestamp': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'exit_price': self.exit_price,
            'exit_signal_details': self.exit_signal_details,
            'exit_signal_score': self.exit_signal_score,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'holding_period_hours': self.holding_period_hours,
            'market_trend_at_entry': self.market_trend_at_entry,
            'long_term_trend_at_entry': self.long_term_trend_at_entry,
            'metadata': self.metadata
        } 