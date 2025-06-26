"""
신호 감지 및 실시간 분석 설정

이 파일은 신호 감지와 실시간 분석에 관련된 설정만을 관리합니다.
- 신호 가중치 및 임계값
- 실시간 분석 주기 및 설정
- 시장 추세에 따른 조정 계수
- 예측 신호 설정
"""

# ====================
# --- 실시간 분석 주기 설정 ---
# ====================

# 데이터 수집 및 분석 주기 (분 단위)
COLLECTION_INTERVAL_MINUTES = 5         # 매 5분마다 1분봉 데이터 수집 및 분석
INTRADAY_INTERVAL = '1m'                 # 실시간 데이터 조회 간격

# 데이터 조회 기간 설정
LOOKBACK_PERIOD_DAYS_FOR_DAILY = 90     # 일일 분석용 데이터 기간
LOOKBACK_PERIOD_MINUTES_FOR_INTRADAY = 60  # 실시간 분석용 데이터 기간 (분)

# 거래량 증가 필터링을 위한 배수
VOLUME_SURGE_FACTOR = 1.2               # 현재 거래량 > 평균 거래량 * 이 값

# ====================
# --- 신호 가중치 설정 ---
# ====================

# 각 조건이 실시간 신호에 기여하는 점수 (높을수록 중요)
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

# 실시간 신호 발생을 위한 최소 총점
SIGNAL_THRESHOLD = 7

# ====================
# --- 시장 추세별 신호 조정 계수 ---
# ====================

SIGNAL_ADJUSTMENT_FACTORS_BY_TREND = {
    "BULLISH": {
        "trend_follow_buy_adj": 1.2,    # 상승 추세에서 매수 신호 강화
        "trend_follow_sell_adj": 0.5,   # 상승 추세에서 매도 신호 약화
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.2,              # 불리시장에서 거래량은 더 긍정적
        "bb_kc_adj": 1.2,               # 불리시장에서 확장도 더 긍정적
        "pivot_fib_adj": 1.3
    },
    "BEARISH": {
        "trend_follow_buy_adj": 0.5,    # 하락 추세에서 매수 신호 약화
        "trend_follow_sell_adj": 1.2,   # 하락 추세에서 매도 신호 강화
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.2,              # 베어리시장에서 거래량은 하락 확인
        "bb_kc_adj": 1.2,               # 베어리시장에서 확장도 하락 확인
        "pivot_fib_adj": 0.8
    },
    "NEUTRAL": {
        "trend_follow_buy_adj": 0.3,    # 중립장에서 추세 추종 신호 더 약화
        "trend_follow_sell_adj": 0.3,   # 중립장에서 추세 추종 신호 더 약화
        "momentum_reversal_adj": 1.5,   # 중립장에서 반전 신호 가중치 더 높임
        "volume_adj": 1.0,              # 중립장에서 거래량 중립적
        "bb_kc_adj": 1.5,               # 중립장에서 변동성 확장은 더 중요
        "pivot_fib_adj": 1.8            # 중립장에서 지지/저항 신호 중요도 더 높임
    }
}

# ====================
# --- 일일 예측 신호 설정 ---
# ====================

# 일일 예측 작업 실행 시간 (ET 기준)
DAILY_PREDICTION_HOUR_ET = 17          # ET 17:00
DAILY_PREDICTION_MINUTE_ET = 0

# 다음날 매수 가격 예측 시 ATR 기반 범위 설정 승수
PREDICTION_ATR_MULTIPLIER_FOR_RANGE = 0.5  # 예측 가격 ± 0.5 * ATR

# 각 조건이 일일 예측 신호에 기여하는 점수
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

# 일일 예측 신호 발생을 위한 최소 총점
PREDICTION_THRESHOLD = 10

# ====================
# --- 실시간 신호 감지 작업 설정 ---
# ====================

REALTIME_SIGNAL_DETECTION = {
    # 데이터 조회 기간 설정
    "FIB_LOOKBACK_DAYS": 200,                    # 피보나치 레벨 계산용 일봉 데이터 기간
    "LOOKBACK_PERIOD_DAYS_FOR_INTRADAY": 60,     # 시간봉 분석용 데이터 기간
    
    # 최소 데이터 요구사항
    "MIN_HOURLY_DATA_LENGTH": 30,                # 시간봉 최소 데이터 개수
    "MIN_DAILY_DATA_LENGTH": 120,                # 일봉 최소 데이터 개수
    
    # 시장 지수 설정
    "MARKET_INDEX_SYMBOL": "^GSPC",              # 시장 추세 판단용 지수 (S&P 500)
    "MARKET_TREND_SMA_PERIOD": 200,              # 시장 추세 판단용 이동평균 기간
    
    # 장기 추세 설정
    "LONG_TERM_TREND_SMA_PERIOD": 50,            # 장기 추세 판단용 이동평균 기간
    
    # 캐시 설정
    "CACHE_UPDATE_INTERVAL_HOURS": 24,           # 캐시 업데이트 간격 (시간)
    
    # 로깅 설정
    "LOG_DATA_LENGTH": True,                     # 데이터 길이 로깅 여부
    "LOG_LAST_ROWS_COUNT": 3,                    # 마지막 N개 행 로깅
} 