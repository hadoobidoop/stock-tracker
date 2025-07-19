"""
거래 관련 enum 정의
"""

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