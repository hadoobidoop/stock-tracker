"""
기술적 지표 계산 설정 (Stock Bot)

이 파일은 모든 기술적 지표의 계산 파라미터를 중앙집중식으로 관리합니다.

[구성 및 목적]
- 각종 기술적 지표(이동평균, RSI, MACD, 볼린저밴드, 스토캐스틱, ADX, ATR, 거래량 등)의 표준 기간 및 파라미터를 한 곳에서 정의합니다.
- 시간 프레임별(일봉, 시간봉)로 별도의 설정을 제공하여, 전략별/분석별로 일관된 기준을 유지할 수 있습니다.
- 피보나치 레벨 등 특수 분석용 파라미터도 포함합니다.
- 통합 딕셔너리(TECHNICAL_INDICATORS)는 단일 함수에서 여러 지표를 일괄 계산할 때 사용합니다.

[실전 활용 예시]
- 각 Detector/전략/분석 서비스에서 본 파일의 설정값을 import하여, 파라미터 변경 시 전체 전략에 자동 반영됩니다.
- 백테스트, 실시간 신호, 리포트 등 다양한 분석 파이프라인에서 재사용됩니다.
- 파라미터 튜닝 시, 본 파일만 수정하면 전체 시스템에 일관성 있게 적용됩니다.

[구조]
1. DAILY_INDICATORS: 일봉(1D) 기준 장기 추세/지지/저항 분석용
2. HOURLY_INDICATORS: 시간봉(1H) 기준 단기/실시간 신호 분석용
3. TECHNICAL_INDICATORS: 주요 지표 파라미터를 한 번에 일괄 제공(통합)
4. FIBONACCI_LEVELS 등: 피보나치 분석용 파라미터

"""

# ====================
# --- 일봉(1D) 기반 지표 설정 ---
# ====================
# 장기 추세, 주요 지지/저항, 스윙 분석 등에 사용
DAILY_INDICATORS = {
    "SMA_PERIODS": [20, 50, 200], # 20일, 50일, 200일 이동평균 (장기 추세/지지선)
    "RSI_PERIOD": 14,             # 14일 RSI (과매수/과매도, 모멘텀)
    "ADX_PERIOD": 14,             # 14일 ADX (추세 강도)
    "BB_PERIOD": 20,              # 20일 볼린저 밴드 (변동성)
    "BB_STD_DEV": 2.0,            # 볼린저 밴드 표준편차
    "FIB_LOOKBACK_DAYS": 200,     # 피보나치/스윙 분석용 lookback 기간(일)
}

# ====================
# --- 시간봉(1H) 기반 지표 설정 ---
# ====================
# 단기/실시간 신호, 스캘핑, 모멘텀, 변동성 분석 등에 사용
HOURLY_INDICATORS = {
    "SMA_PERIODS": [5, 20],       # 5시간, 20시간 이동평균 (단기 추세/지지선)
    "MACD_FAST": 12,              # 12시간 MACD 빠른 EMA
    "MACD_SLOW": 26,              # 26시간 MACD 느린 EMA
    "MACD_SIGNAL": 9,             # 9시간 MACD 신호선
    "STOCH_K_PERIOD": 14,         # 14시간 스토캐스틱 %K
    "STOCH_D_PERIOD": 3,          # 3시간 스토캐스틱 %D
    "ATR_PERIOD": 14,             # 14시간 ATR (평균 진폭)
    "VOLUME_SMA_PERIOD": 20,      # 20시간 거래량 이동평균
    "RSI_PERIOD": 14,             # 14시간 RSI
}

# ====================
# --- 통합(일괄) 지표 파라미터 설정 ---
# ====================
# 여러 지표를 한 번에 계산하는 함수에서 사용 (calculate_all_indicators 등)
TECHNICAL_INDICATORS = {
    "SMA_PERIODS": [5, 20, 60],   # 대표 SMA 기간 (5, 20, 60)
    "RSI_PERIOD": 14,             # RSI 기간
    "MACD_FAST": 12,              # MACD 빠른 EMA
    "MACD_SLOW": 26,              # MACD 느린 EMA
    "MACD_SIGNAL": 9,             # MACD 신호선
    "STOCH_K_PERIOD": 14,         # 스토캐스틱 %K
    "STOCH_D_PERIOD": 3,          # 스토캐스틱 %D
    "BB_PERIOD": 20,              # 볼린저 밴드 기간
    "BB_STD_DEV": 2.0,            # 볼린저 밴드 표준편차
    "ATR_PERIOD": 14,             # ATR 기간
    "VOLUME_SMA_PERIOD": 20,      # 거래량 이동평균 기간
    "ADX_PERIOD": 14,             # ADX 기간
}

# ====================
# --- 피보나치 레벨 및 분석 파라미터 ---
# ====================
# 피보나치 되돌림/확장 분석, 스윙 고점/저점 탐색 등에 사용
FIB_RETRACEMENT_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786] # 표준 피보나치 되돌림 비율

FIBONACCI_LEVELS = {
    "LEVELS": [0, 23.6, 38.2, 50.0, 61.8, 100],  # 주요 피보나치 레벨(%)
    "LOOKBACK_DAYS": 200,                        # 분석용 데이터 기간(일)
}

FIB_LOOKBACK_DAYS = 60 # 피보나치 스윙 분석용 lookback 기간(일) 