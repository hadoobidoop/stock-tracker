"""
예측 신호(일일/스윙 등) 관련 설정
- 일일 예측 신호 발생 기준, 점수, ATR 기반 범위 등
"""

DAILY_PREDICTION_HOUR_ET = 17          # ET 17:00
DAILY_PREDICTION_MINUTE_ET = 0
PREDICTION_ATR_MULTIPLIER_FOR_RANGE = 0.5  # 예측 가격 ± 0.5 * ATR

PREDICTION_SIGNAL_WEIGHTS = {
    "pivot_s1_near": 5,                 # S1 근처
    "pivot_s2_near": 5,                 # S2 근처
    "fib_382_near": 4,                  # 피보나치 38.2% 근처
    "fib_500_near": 4,                  # 피보나치 50% 근처
    "fib_618_near": 5,                  # 피보나치 61.8% 근처
    "rsi_oversold_daily": 3,            # 일일 RSI 과매도
    "atr_reasonable_daily": 2,          # 일일 ATR이 적정할 때
    "bullish_candle_daily": 2           # 강세 캔들 패턴
}

PREDICTION_THRESHOLD = 10 