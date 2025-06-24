from typing import List

# 분석할 주식 심볼 목록 (이곳에서 쉽게 추가/제거 가능)
# 예: S&P 500의 주요 기술주
STOCK_SYMBOLS: List[str] = [
    "VDC", "TSLL", "TQQQ", "SCHD", "JEPQ", "JEPI",
    "GLDM", "CIBR", "BITX",
    "ARKG", "PFE", "KHC", "LLY", "WM",
    "GOOGL", "AMZN", "VEEV", "MRK", "DUK", "NUE", "X", "NEE"
]

# 시장 지수 티커 (S&P 500)
MARKET_INDEX_TICKER: str = "^GSPC"

# OHLCV 데이터 수집 설정
OHLCV_COLLECTION = {
    # 일봉 데이터 설정
    "DAILY": {
        "PERIOD": "6mo",  # 6개월치 데이터 조회
        "INTERVAL": "1d",  # 일봉
        "MIN_DATA_LENGTH": 120,  # 최소 120일치 데이터 필요
        "DAYS_TO_KEEP": 180  # 180일치 데이터 유지
    },
    # 시간봉 데이터 설정
    "HOURLY": {
        "PERIOD": "14d",  # 14일치 데이터 조회
        "INTERVAL": "1h",  # 시간봉
        "MIN_DATA_LENGTH": 48,  # 최소 48시간치 데이터 필요
        "DAYS_TO_KEEP": 14  # 14일치 데이터 유지
    },
    # API 재시도 설정
    "RETRY": {
        "WAIT_SECONDS": 2,  # 재시도 전 대기 시간
        "MAX_ATTEMPTS": 2  # 최대 시도 횟수
    },
    # API 호출 제어 설정
    "API_CONTROL": {
        "PAGE_SIZE": 20,  # 한 번에 조회할 종목 수
        "RATE_LIMIT_DELAY_SECONDS": 30  # 각 페이지 조회 후 대기 시간 (초)
    }
}
