"""
신호 가중치 및 임계값 설정
- 각 신호 조건별 점수, 신호 발생 임계값 등
"""

SIGNAL_WEIGHTS = {
    "golden_cross_sma": 5,              # SMA 골든/데드 크로스 (추세 전환)
    "macd_cross": 5,                    # MACD 골든/데드 크로스 (모멘텀 전환)
    "volume_surge": 4,                  # 거래량 급증 (신호의 강도 확인)
    "adx_strong_trend": 4,              # ADX 강한 추세 (추세 강도 확인)
    "rsi_bounce_drop": 3,               # RSI 과매수/과매도 구간 이탈
    "stoch_cross": 3,                   # 스토캐스틱 매수/매도 크로스
    "bb_squeeze_expansion": 3,          # 볼린저 밴드/켈트너 채널 스퀴즈 및 확장
    "rsi_bb_reversal": 6,               # RSI와 볼린저 밴드 조합 반전 신호
    "macd_volume_confirm": 7,           # MACD와 거래량 조합 확인 신호
    "rsi_stoch_confirm": 6,             # RSI와 스토캐스틱 조합 확인 신호
    "pivot_momentum_reversal": 8,       # 피봇/피보나치 + 모멘텀 반전 신호
    "fib_momentum_reversal": 8,         # 피보나치 + 모멘텀 반전 신호
    "candlestick_bullish_pattern": 2,   # 캔들스틱 강세 패턴
    "candlestick_bearish_pattern": 2    # 캔들스틱 약세 패턴
}

SIGNAL_THRESHOLD = 7 