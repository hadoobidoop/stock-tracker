import enum


class TrendType(str, enum.Enum):
    """추세의 종류를 정의하는 Enum 클래스"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SignalType(str, enum.Enum):
    """거래 신호 타입을 정의하는 Enum 클래스"""
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL" 