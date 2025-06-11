# config.py

import os

from dotenv import load_dotenv

# 텔레그램 봇 토큰은 @BotFather를 통해 새 봇을 생성하여 얻을 수 있습니다.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
# 텔레그램 채팅 ID는 봇에게 메시지를 보낸 후
# https://api.telegram.org/bot{YOUR_TELEGRAM_BOT_TOKEN}/getUpdates 에서 확인할 수 있습니다.
# 그룹 채팅 ID는 -100으로 시작합니다.
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

# ====================
# --- 데이터베이스 설정 (MySQL 호환) ---
# ====================
# 환경 변수에서 AWS RDS 접속 정보를 가져옵니다.
# 미리 서버 환경에 아래 변수들을 설정해두어야 합니다.
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# SQLAlchemy MySQL 연결 문자열 형식 (mysql+mysqlconnector://<user>:<password>@<host>[:<port>]/<dbname>)
# charset=utf8mb4 : 다양한 언어와 이모지를 지원하기 위한 필수 설정입니다.
DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)
DATA_RETENTION_DAYS = 30

LOOKBACK_PERIOD_DAYS_FOR_INTRADAY=1
# ====================
# 모니터링할 주식 심볼 목록 (미국 주식)
# ====================
STOCK_SYMBOLS = [
    "MSFT"
]

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
INTRADAY_INTERVAL = '1m'  # <--- 여기에 정의되어 있습니다.
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
# 로깅 설정
# ====================
LOG_FILE = "stock_analyzer.log"  # 로그 파일 이름
