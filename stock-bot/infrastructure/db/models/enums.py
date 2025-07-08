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


class MarketIndicatorType(str, enum.Enum):
    """시장 지표 타입을 정의하는 Enum 클래스"""
    BUFFETT_INDICATOR = "BUFFETT_INDICATOR"  # 버핏 지수 (Wilshire 5000 / GDP)
    VIX = "VIX"  # 공포지수
    PUT_CALL_RATIO = "PUT_CALL_RATIO"  # 풋/콜 비율
    FEAR_GREED_INDEX = "FEAR_GREED_INDEX"  # Fear & Greed Index
    US_10Y_TREASURY_YIELD = "US_10Y_TREASURY_YIELD"  # 10년 국채 수익률
    DXY = "DXY"  # 달러 지수
    GOLD_PRICE = "GOLD_PRICE"  # 금 가격 (GC=F)
    CRUDE_OIL_PRICE = "CRUDE_OIL_PRICE"  # 원유 가격 (CL=F)
    SP500_INDEX = "SP500_INDEX"  # S&P 500 지수 (^GSPC)
    SP500_SMA_200 = "SP500_SMA_200"  # S&P 500 지수의 200일 이동평균
    # 추후 추가될 지표들을 위한 여백 