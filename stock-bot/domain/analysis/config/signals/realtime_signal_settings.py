"""
실시간 신호 감지/분석 관련 설정
- 데이터 수집/분석 주기, 실시간 분석용 기간, 거래량 필터, 실시간 신호 감지 파라미터 등
"""

COLLECTION_INTERVAL_MINUTES = 5         # 매 5분마다 1분봉 데이터 수집 및 분석
INTRADAY_INTERVAL = '1m'                 # 실시간 데이터 조회 간격
LOOKBACK_PERIOD_DAYS_FOR_DAILY = 90     # 일일 분석용 데이터 기간
LOOKBACK_PERIOD_MINUTES_FOR_INTRADAY = 60  # 실시간 분석용 데이터 기간 (분)
VOLUME_SURGE_FACTOR = 1.2               # 현재 거래량 > 평균 거래량 * 이 값

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