# ====================
# --- 실시간(분 단위) 분석 설정 ---
# ====================
# 데이터 수집 및 분석 주기 (분 단위)
# yfinance의 1분봉 데이터는 7일 이내의 기간만 조회 가능하며, 잦은 호출 시 IP 밴이 될 수 있습니다.
# 5분 또는 15분 간격 추천 (API 호출 제한 및 데이터 지연 고려)
COLLECTION_INTERVAL_MINUTES = 5  # 매 5분마다 1분봉 데이터 수집 및 분석

# 거래량 증가 필터링을 위한 배수 (현재 거래량 > 평균 거래량 * 이 값)
VOLUME_SURGE_FACTOR = 1.2

# 각 조건이 실시간 신호에 기여하는 점수 (높을수록 중요)
# TA-Lib 의존성으로 인해 캔들스틱 패턴(bullish_engulfing, hammer_pattern, bearish_engulfing, shooting_star_pattern)은
# 실제 코드에서는 사용되지 않지만, 가중치 관리 목적으로 여기에 포함합니다.
SIGNAL_WEIGHTS = {
    "golden_cross_sma": 4,  # SMA 골든/데드 크로스 (추세 전환)
    "macd_cross": 4,  # MACD 골든/데드 크로스 (모멘텀 전환)
    "volume_surge": 3,  # 거래량 급증 (신호의 강도 확인)
    "adx_strong_trend": 3,  # ADX 강한 추세 (추세 강도 확인)
    "rsi_bounce_drop": 2,  # RSI 과매수/과매도 구간 이탈
    "stoch_cross": 2,  # 스토캐스틱 매수/매도 크로스
    "bb_squeeze_expansion": 2,  # 볼린저 밴드/켈트너 채널 스퀴즈 및 확장 (변동성 변화)
    "rsi_bb_reversal": 5,  # RSI와 볼린저 밴드 조합 반전 신호 (새로운 가중치)
    "macd_volume_confirm": 6,  # MACD와 거래량 조합 확인 신호 (새로운 가중치)
    "rsi_stoch_confirm": 5,  # RSI와 스토캐스틱 조합 확인 신호 (새로운 가중치)
    "pivot_momentum_reversal": 7,  # 피봇/피보나치 + 모멘텀 반전 신호 (새로운 가중치, 높은 신뢰도)
    "fib_momentum_reversal": 7,  # 피보나치 + 모멘텀 반전 신호 (새로운 가중치, 높은 신뢰도)
    "candlestick_bullish_pattern": 1,  # 캔들스틱 강세 패턴 (구현 시)
    "candlestick_bearish_pattern": 1  # 캔들스틱 약세 패턴 (구현 시)
}

# 실시간 신호 발생을 위한 최소 총점
SIGNAL_THRESHOLD = 12

# 시장 추세에 따른 신호 가중치 조정 계수 (새로 추가)
SIGNAL_ADJUSTMENT_FACTORS_BY_TREND = {
    "BULLISH": {
        "trend_follow_buy_adj": 1.0,
        "trend_follow_sell_adj": 0.3,
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.0,  # 불리시장에서 거래량은 긍정적
        "bb_kc_adj": 1.0,  # 불리시장에서 확장도 긍정적
        "pivot_fib_adj": 1.2
    },
    "BEARISH": {
        "trend_follow_buy_adj": 0.3,
        "trend_follow_sell_adj": 1.0,
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.0,  # 베어리시장에서 거래량은 하락 확인
        "bb_kc_adj": 1.0,  # 베어리시장에서 확장도 하락 확인
        "pivot_fib_adj": 0.7
    },
    "NEUTRAL": {
        "trend_follow_buy_adj": 0.1,
        "trend_follow_sell_adj": 0.1,
        "momentum_reversal_adj": 1.2,  # 중립장에서 반전 신호 가중치 높임
        "volume_adj": 0.8,  # 중립장에서 거래량 급증은 신뢰도 약간 낮음
        "bb_kc_adj": 1.2,  # 중립장에서 변동성 확장은 중요
        "pivot_fib_adj": 1.5  # 중립장에서 지지/저항 신호 중요도 높임
    }
}

# ====================
# --- 다음 날 매수 가격 예측 설정 (일일 작업) ---
# ====================
# 일일 예측 작업 실행 시간 (ET 기준)
# 미국 시장 마감 후 (ET 16:00) 데이터를 가져오기 위해 ET 17:00 (한국 시간 오전 6시 or 7시 (서머타임))으로 설정
DAILY_PREDICTION_HOUR_ET = 17
DAILY_PREDICTION_MINUTE_ET = 0
INTRADAY_INTERVAL = '1m'  # 실시간 데이터 조회 간격
LOOKBACK_PERIOD_DAYS_FOR_DAILY = 90
# 실시간 데이터 조회 기간 (예: 60분봉 데이터를 위해 60분)
LOOKBACK_PERIOD_MINUTES_FOR_INTRADAY = 60
# 피보나치 되돌림 수준 (백분율이 아닌 비율로)
# 0.236, 0.382, 0.5, 0.618, 0.786
FIB_RETRACEMENT_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
# 피보나치 스윙 고점/저점 탐색 기간 (일 단위)
FIB_LOOKBACK_DAYS = 60  # 최근 60일 데이터에서 스윙 고점/저점 탐색

# 다음날 매수 가격 예측 시 ATR 기반 범위 설정 승수
PREDICTION_ATR_MULTIPLIER_FOR_RANGE = 0.5  # 예측 가격 ± 0.5 * ATR

# 각 조건이 일일 예측 신호에 기여하는 점수 (높을수록 중요)
# 이전에 논의했던 예측 점수 로직에 맞춰 이름과 점수를 조정했습니다.
PREDICTION_SIGNAL_WEIGHTS = {
    "pivot_s1_near": 5,  # S1 근처
    "pivot_s2_near": 5,  # S2 근처 (S1과 동일 가중치로, 가장 중요한 지지선으로 간주)
    "fib_382_near": 4,  # 피보나치 38.2% 근처
    "fib_500_near": 4,  # 피보나치 50% 근처
    "fib_618_near": 5,  # 피보나치 61.8% 근처 (강력한 되돌림 지지)
    "rsi_oversold_daily": 3,  # 일일 RSI 과매도
    "atr_reasonable_daily": 2,  # 일일 ATR이 너무 높지 않아 변동성이 합리적일 때 (가격 범위 예측이 의미있을 때)
    # 캔들스틱 패턴은 TA-Lib 없이 구현 어려워 제외 (가중치 관리 목적으로만 포함)
    "bullish_candle_daily": 2
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
    "MIN_HOURLY_DATA_LENGTH": 60,                # 시간봉 최소 데이터 개수
    "MIN_DAILY_DATA_LENGTH": 200,                # 일봉 최소 데이터 개수
    
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

# ====================
# --- 기술적 지표 계산 설정 (시간 프레임별 분리) ---
# ====================

# 일봉 기반 지표 (장기 추세 및 지지/저항 분석용)
DAILY_TECHNICAL_INDICATORS = {
    # 이동평균 설정 (추세 분석용)
    "SMA_PERIODS": [20, 50, 200],               # 20일, 50일, 200일 이동평균
    
    # RSI 설정 (과매수/과매도 판단용)
    "RSI_PERIOD": 14,                           # 14일 RSI (전통적)
    
    # ADX 설정 (추세 강도 분석용)
    "ADX_PERIOD": 14,                           # 14일 ADX
    
    # 볼린저 밴드 설정 (변동성 및 지지/저항용)
    "BB_PERIOD": 20,                            # 20일 볼린저 밴드
    "BB_STD_DEV": 2.0,                          # 볼린저 밴드 표준편차
    
    # 피보나치 레벨 계산용
    "FIB_LOOKBACK_DAYS": 200,                   # 200일 데이터로 스윙 고점/저점 탐색
}

# 시간봉 기반 지표 (실시간 매매 신호용)
HOURLY_TECHNICAL_INDICATORS = {
    # 단기 이동평균 (빠른 신호용)
    "SMA_PERIODS": [5, 20],                     # 5시간, 20시간 이동평균
    
    # MACD 설정 (모멘텀 신호용)
    "MACD_FAST": 12,                            # 12시간 빠른 EMA
    "MACD_SLOW": 26,                            # 26시간 느린 EMA
    "MACD_SIGNAL": 9,                           # 9시간 신호선
    
    # 스토캐스틱 설정 (단기 과매수/과매도 신호)
    "STOCH_K_PERIOD": 14,                       # 14시간 %K
    "STOCH_D_PERIOD": 3,                        # 3시간 %D
    
    # ATR 설정 (실시간 손절가 설정용)
    "ATR_PERIOD": 14,                           # 14시간 ATR
    
    # 거래량 설정 (실시간 거래량 분석)
    "VOLUME_SMA_PERIOD": 20,                    # 20시간 거래량 평균
    
    # RSI 설정 (빠른 과매수/과매도 신호)
    "RSI_PERIOD": 14,                           # 14시간 RSI (보조 신호용)
}

# 기존 호환성을 위한 통합 설정 (현재 사용 중인 설정)
TECHNICAL_INDICATORS = {
    # 이동평균 설정
    "SMA_PERIODS": [5, 20, 60],                  # 계산할 SMA 기간들
    
    # RSI 설정
    "RSI_PERIOD": 14,                            # RSI 계산 기간
    
    # MACD 설정
    "MACD_FAST": 12,                             # MACD 빠른 이동평균
    "MACD_SLOW": 26,                             # MACD 느린 이동평균
    "MACD_SIGNAL": 9,                            # MACD 신호선
    
    # 스토캐스틱 설정
    "STOCH_K_PERIOD": 14,                        # 스토캐스틱 %K 기간
    "STOCH_D_PERIOD": 3,                         # 스토캐스틱 %D 기간
    
    # 볼린저 밴드 설정
    "BB_PERIOD": 20,                             # 볼린저 밴드 기간
    "BB_STD_DEV": 2.0,                           # 볼린저 밴드 표준편차
    
    # ATR 설정
    "ATR_PERIOD": 14,                            # ATR 계산 기간
    
    # 거래량 설정
    "VOLUME_SMA_PERIOD": 20,                     # 거래량 이동평균 기간
    
    # ADX 설정
    "ADX_PERIOD": 14,                            # ADX 계산 기간
}

# ====================
# --- 피보나치 레벨 설정 ---
# ====================
FIBONACCI_LEVELS = {
    "LEVELS": [0, 23.6, 38.2, 50.0, 61.8, 100], # 계산할 피보나치 레벨들
    "LOOKBACK_DAYS": 200,                        # 피보나치 계산용 데이터 기간
}
