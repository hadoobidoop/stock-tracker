# main.py

import logging
import pytz # 시간대 처리를 위해 필요
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    STOCK_SYMBOLS, COLLECTION_INTERVAL_MINUTES, SIGNAL_THRESHOLD, SIGNAL_WEIGHTS,
    DAILY_PREDICTION_HOUR_ET, DAILY_PREDICTION_MINUTE_ET,
    INTRADAY_INTERVAL, LOOKBACK_PERIOD_DAYS_FOR_DAILY,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LOG_FILE
)
from data_collector import get_ohlcv_data
from indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
from price_predictor import predict_next_day_buy_price
from signal_detector import detect_weighted_signals
from notifier import send_telegram_message, format_prediction_message, format_signal_message

# ====================
# 로깅 설정
# ====================
# 핸들러 설정

console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO, # 기본 로깅 레벨
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        console_handler
    ]
)
logger = logging.getLogger(__name__)

# ====================
# 헬퍼 함수
# ====================
def get_current_et_time():
    """현재 ET(미국 동부 시간)를 반환합니다."""
    et_timezone = pytz.timezone('America/New_York')
    return datetime.now(et_timezone)

def is_market_open(current_et: datetime) -> bool:
    """
    미국 주식 시장이 현재 열려있는지 확인합니다 (주중 오전 9:30 ~ 오후 4:00 ET).
    """
    # 주말 (토요일=5, 일요일=6)
    if current_et.weekday() >= 5:
        return False

    # 공휴일 (하드코딩 또는 API 연동 필요, 여기서는 생략)
    # 예: if current_et.strftime('%Y-%m-%d') in ["2025-01-01", "2025-07-04"]: return False

    # 장 시간
    market_open_time = current_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close_time = current_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open_time <= current_et < market_close_time

# ====================
# 스케줄링 작업 정의
# ====================

def run_daily_buy_price_prediction_job():
    """
    매일 장 마감 후 실행되는 다음 날 예상 매수 가격 예측 작업
    """
    logger.info("Starting daily buy price prediction job...")
    current_et = get_current_et_time()
    date_str_for_prediction = current_et.strftime('%Y-%m-%d') # 예측 실행 날짜 (오늘)

    # 일봉 데이터는 여전히 각 종목별로 가져오는 것이 일반적 (전체 데이터 한 번에 가져오기 어려움)
    for symbol in STOCK_SYMBOLS:
        df_daily = get_ohlcv_data(
            symbols=symbol, # get_ohlcv_data의 인자 이름을 symbols로 변경했으므로 일관성 유지
            period=f"{LOOKBACK_PERIOD_DAYS_FOR_DAILY}d", # yfinance period 형식
            interval='1d' # 일봉 데이터
        )

        if df_daily.empty or len(df_daily) < 1:
            logger.warning(f"Skipping daily prediction for {symbol}: No daily data available or insufficient length.")
            continue

        # 예측은 전일 종가 기준으로 이루어지므로, 최신 데이터의 종가를 전달
        prev_day_close = df_daily.iloc[-1]['Close']
        prediction_timestamp = current_et.strftime('%Y-%m-%d %H:%M:%S ET')

        # 다음 날 매수 가격 예측
        prediction_result = predict_next_day_buy_price(df_daily, symbol)

        if prediction_result:
            # notifier에 필요한 추가 정보 주입
            prediction_result['prev_day_close'] = prev_day_close
            prediction_result['prediction_timestamp'] = prediction_timestamp
            message = format_prediction_message(prediction_result)
            send_telegram_message(message)
        else:
            logger.info(f"No strong buy price prediction for {symbol} today.")
    logger.info("Daily buy price prediction job completed.")


def run_realtime_signal_detection_job():
    """
    장 중 주기적으로 실행되는 실시간 매수/매도 신호 감지 작업
    """
    current_et = get_current_et_time()
    if not is_market_open(current_et):
        logger.info(f"Market is closed at {current_et.strftime('%Y-%m-%d %H:%M ET')}. Skipping real-time signal detection.")
        return

    logger.info("Starting real-time signal detection job...")

    # 모든 종목의 1분봉 데이터를 한 번에 가져오기 (yfinance는 7일 이내의 1분봉만 지원)
    period_str = '7d' # 최대 7일로 설정

    # 모든 종목의 데이터를 한 번에 요청 (get_ohlcv_data 함수가 여러 심볼을 받도록 수정됨)
    all_intraday_data = get_ohlcv_data(
        symbols=STOCK_SYMBOLS, # STOCK_SYMBOLS 리스트 전체를 전달
        period=period_str,
        interval=INTRADAY_INTERVAL
    )

    # 데이터가 딕셔너리 형태로 반환되었는지 확인
    if not isinstance(all_intraday_data, dict) or not all_intraday_data:
        logger.error(f"Failed to fetch any intraday data for all symbols. Expected dictionary, got {type(all_intraday_data)}.")
        return # 데이터 가져오기 실패 시 함수 종료

    # 가져온 각 종목의 데이터를 순회하며 처리
    # 이제 for 루프는 yfinance 호출 부분이 아니라, 가져온 데이터 딕셔너리를 순회합니다.
    for symbol, df_intraday in all_intraday_data.items():
        if df_intraday.empty or len(df_intraday) < max(20, 60): # 최소 20봉 이상 (BB, KC 기본 20)
            logger.warning(f"Skipping real-time signal detection for {symbol}: Not enough intraday data available ({len(df_intraday)} rows). Need at least 60 rows for indicators.")
            continue

        # 1분봉 데이터 기반 지표 계산
        df_with_intraday_indicators = calculate_intraday_indicators(df_intraday)

        if df_with_intraday_indicators.empty:
            logger.warning(f"Skipping real-time signal detection for {symbol}: Indicators could not be calculated (DataFrame became empty after dropna).")
            continue

        # 신호 감지를 위한 충분한 데이터가 있는지 다시 확인 (dropna 이후 길이가 줄어들 수 있음)
        if len(df_with_intraday_indicators) < 2: # 최소 2봉 (현재 봉, 이전 봉)
            logger.warning(f"Skipping real-time signal detection for {symbol}: Insufficient intraday data after indicator calculation ({len(df_with_intraday_indicators)} rows).")
            continue

        # 가중치 기반 신호 감지
        signal_result = detect_weighted_signals(
            df_with_intraday_indicators,
            symbol # ticker
        )

        if signal_result:
            # notifier에 필요한 current_data와 prev_data 주입 (detect_weighted_signals에서 반환받아 사용)
            latest_data = df_with_intraday_indicators.iloc[-1]
            prev_data = df_with_intraday_indicators.iloc[-2]

            message = format_signal_message(
                ticker=symbol,
                signal_type=signal_result['type'],
                signal_score=signal_result['score'],
                signal_details_list=signal_result['details'],
                current_data=latest_data,
                prev_data=prev_data # 이전 데이터도 메시지에 필요할 경우 대비
            )
            send_telegram_message(message)
        else:
            # logger.debug(f"No strong real-time signal for {symbol} at {current_et.strftime('%H:%M ET')}.")
            pass # 신호 없으면 메시지 전송 안함

    logger.info("Real-time signal detection job completed.")


# ====================
# 스케줄러 실행
# ====================
if __name__ == "__main__":
    logger.info("Starting Stock Analyzer Bot...")

    scheduler = BackgroundScheduler(timezone=pytz.timezone('America/New_York'))

    # 일일 예측 작업 스케줄링 (매일 지정된 ET 시간에 실행)
    scheduler.add_job(
        run_daily_buy_price_prediction_job,
        trigger=CronTrigger(
            hour=DAILY_PREDICTION_HOUR_ET,
            minute=DAILY_PREDICTION_MINUTE_ET,
            day_of_week='mon-fri', # 주중만 실행
            timezone=pytz.timezone('America/New_York')
        ),
        id='daily_prediction_job',
        name='Daily Buy Price Prediction',
        misfire_grace_time=60*5 # 5분 내에 실행되지 않으면 다음 기회에
    )
    logger.info(f"Daily buy price prediction job scheduled for {DAILY_PREDICTION_HOUR_ET}:{DAILY_PREDICTION_MINUTE_ET} ET (Mon-Fri).")

    # 실시간 신호 감지 작업 스케줄링 (장 중 주기적으로 실행)
    scheduler.add_job(
        run_realtime_signal_detection_job,
        'interval',
        minutes=COLLECTION_INTERVAL_MINUTES,
        id='realtime_signal_job',
        name='Real-time Signal Detection',
        # is_market_open 함수로 장 중 시간대에만 실행되도록 코드로 필터링
        # misfire_grace_time=None # 인터벌 잡은 보통 misfire_grace_time을 사용하지 않아 즉시 실행 시도
    )
    logger.info(f"Real-time signal detection job scheduled every {COLLECTION_INTERVAL_MINUTES} minutes during market hours.")


    try:
        scheduler.start()
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        # 메인 스레드가 종료되지 않도록 무한 루프
        while True:
            import time
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
