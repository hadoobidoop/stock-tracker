# 신호 감지 점수 임계값
SIGNAL_THRESHOLD = 10.0

# 개별 신호 가중치
SIGNAL_WEIGHTS = {
    "golden_cross_sma": 2.5,
    "macd_cross": 2.5,
    "adx_strong_trend": 1.5,
    "rsi_bounce_drop": 2.0,
    "stoch_cross": 2.0,
    "volume_surge": 1.0,
    "bb_squeeze_expansion": 3.0,
    "candlestick_bullish_pattern": 1.5,
    "candlestick_bearish_pattern": 1.5,

    # 복합 신호 가중치
    "macd_volume_confirm": 3.5,
    "rsi_bb_reversal": 3.0,
    "rsi_stoch_confirm": 3.0,
    "pivot_momentum_reversal": 4.0,
    "fib_momentum_reversal": 4.0,
}


# 거래량 급증 계수 (평균 거래량 대비)
VOLUME_SURGE_FACTOR = 2.0

# 지지/저항 예측 시 ATR 계수
PREDICTION_ATR_MULTIPLIER_FOR_RANGE = 0.5


# 시장 추세에 따른 신호 조정 계수
SIGNAL_ADJUSTMENT_FACTORS_BY_TREND = {
    "BULLISH": {
        "trend_follow_buy_adj": 1.2,   # 추세 추종 매수 신호 가중치 증가
        "trend_follow_sell_adj": 0.8,  # 추세 추종 매도 신호 가중치 감소
        "momentum_reversal_adj": 1.1,  # 모멘텀 반전 신호 가중치 증가
        "volume_adj": 1.1,
        "bb_kc_adj": 1.1,
        "pivot_fib_adj": 1.2           # 지지/저항 기반 신호 가중치 증가
    },
    "BEARISH": {
        "trend_follow_buy_adj": 0.8,   # 추세 추종 매수 신호 가중치 감소
        "trend_follow_sell_adj": 1.2,  # 추세 추종 매도 신호 가중치 증가
        "momentum_reversal_adj": 1.1,
        "volume_adj": 1.1,
        "bb_kc_adj": 1.1,
        "pivot_fib_adj": 1.2           # 지지/저항 기반 신호 가중치 증가
    },
    "NEUTRAL": {
        "trend_follow_buy_adj": 1.0,
        "trend_follow_sell_adj": 1.0,
        "momentum_reversal_adj": 1.0,
        "volume_adj": 1.0,
        "bb_kc_adj": 1.0,
        "pivot_fib_adj": 1.0
    }
}
