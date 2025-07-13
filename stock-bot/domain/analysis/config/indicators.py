"""
기술적 지표 계산 설정

이 파일은 모든 기술적 지표의 계산 파라미터만을 관리합니다.
- RSI, MACD, SMA, 볼린저 밴드 등의 기간 설정
- 시간 프레임별 지표 설정 (일봉, 시간봉)
- 피보나치 레벨 설정
"""

# ====================
# --- 기본 기술적 지표 설정 ---
# ====================

# 주요 지표 기간 설정
RSI_PERIOD = 14                 # RSI 계산 기간
MACD_FAST = 12                  # MACD 빠른 이동평균  
MACD_SLOW = 26                  # MACD 느린 이동평균
MACD_SIGNAL = 9                 # MACD 신호선
STOCH_K_PERIOD = 14             # 스토캐스틱 %K 기간
STOCH_D_PERIOD = 3              # 스토캐스틱 %D 기간
BB_PERIOD = 20                  # 볼린저 밴드 기간
BB_STD_DEV = 2.0                # 볼린저 밴드 표준편차
ATR_PERIOD = 14                 # ATR 계산 기간
ADX_PERIOD = 14                 # ADX 계산 기간
VOLUME_SMA_PERIOD = 20          # 거래량 이동평균 기간

# 이동평균 기간들
SMA_PERIODS = [5, 20, 60]       # 계산할 SMA 기간들

# ====================
# --- 시간 프레임별 지표 설정 ---
# ====================

# 일봉 기반 지표 (장기 추세 및 지지/저항 분석용)
DAILY_INDICATORS = {
    "SMA_PERIODS": [20, 50, 200],       # 20일, 50일, 200일 이동평균
    "RSI_PERIOD": 14,                   # 14일 RSI
    "ADX_PERIOD": 14,                   # 14일 ADX  
    "BB_PERIOD": 20,                    # 20일 볼린저 밴드
    "BB_STD_DEV": 2.0,                  # 볼린저 밴드 표준편차
    "FIB_LOOKBACK_DAYS": 200,           # 200일 데이터로 스윙 고점/저점 탐색
}

# 시간봉 기반 지표 (실시간 매매 신호용)
HOURLY_INDICATORS = {
    "SMA_PERIODS": [5, 20],             # 5시간, 20시간 이동평균
    "MACD_FAST": 12,                    # 12시간 빠른 EMA
    "MACD_SLOW": 26,                    # 26시간 느린 EMA
    "MACD_SIGNAL": 9,                   # 9시간 신호선
    "STOCH_K_PERIOD": 14,               # 14시간 %K
    "STOCH_D_PERIOD": 3,                # 3시간 %D
    "ATR_PERIOD": 14,                   # 14시간 ATR
    "VOLUME_SMA_PERIOD": 20,            # 20시간 거래량 평균
    "RSI_PERIOD": 14,                   # 14시간 RSI
}

# 기존 호환성을 위한 통합 설정
TECHNICAL_INDICATORS = {
    "SMA_PERIODS": SMA_PERIODS,
    "RSI_PERIOD": RSI_PERIOD,
    "MACD_FAST": MACD_FAST,
    "MACD_SLOW": MACD_SLOW,
    "MACD_SIGNAL": MACD_SIGNAL,
    "STOCH_K_PERIOD": STOCH_K_PERIOD,
    "STOCH_D_PERIOD": STOCH_D_PERIOD,
    "BB_PERIOD": BB_PERIOD,
    "BB_STD_DEV": BB_STD_DEV,
    "ATR_PERIOD": ATR_PERIOD,
    "VOLUME_SMA_PERIOD": VOLUME_SMA_PERIOD,
    "ADX_PERIOD": ADX_PERIOD,
}

# ====================
# --- 피보나치 레벨 설정 ---
# ====================

# 피보나치 되돌림 수준 (비율)
FIB_RETRACEMENT_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]

# 피보나치 설정
FIBONACCI_LEVELS = {
    "LEVELS": [0, 23.6, 38.2, 50.0, 61.8, 100],  # 계산할 피보나치 레벨들
    "LOOKBACK_DAYS": 200,                         # 피보나치 계산용 데이터 기간
}

# 피보나치 스윙 고점/저점 탐색 기간
FIB_LOOKBACK_DAYS = 60 