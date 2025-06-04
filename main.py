# main.py

import logging

import pandas as pd
import pytz # 시간대 처리를 위해 필요
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    STOCK_SYMBOLS, COLLECTION_INTERVAL_MINUTES, SIGNAL_THRESHOLD, SIGNAL_WEIGHTS,
    DAILY_PREDICTION_HOUR_ET, DAILY_PREDICTION_MINUTE_ET,
    INTRADAY_INTERVAL, LOOKBACK_PERIOD_DAYS_FOR_DAILY, FIB_LOOKBACK_DAYS, # FIB_LOOKBACK_DAYS 추가
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

        # get_ohlcv_data가 단일 DataFrame을 반환하는 경우에 대한 처리
        if not isinstance(df_daily, pd.DataFrame) or df_daily.empty or len(df_daily) < 1:
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

    # --- 시장 추세 판단 로직 ---
    market_index_symbol = '^GSPC' # S&P 500 지수
    market_trend = "NEUTRAL" # 기본값

    df_market_daily = get_ohlcv_data(
        symbols=market_index_symbol,
        period="200d", # 200일 SMA 계산을 위해 최소 200일 데이터 필요
        interval='1d'
    )

    if not isinstance(df_market_daily, pd.DataFrame) or df_market_daily.empty:
        logger.warning(f"Could not fetch market index data for {market_index_symbol}. Market trend set to NEUTRAL.")
    else:
        df_market_daily['SMA_200'] = df_market_daily['Close'].rolling(window=200).mean()

        if len(df_market_daily) >= 200 and not pd.isna(df_market_daily.iloc[-1]['SMA_200']):
            latest_market_close = df_market_daily.iloc[-1]['Close']
            latest_market_sma_200 = df_market_daily.iloc[-1]['SMA_200']

            if latest_market_close > latest_market_sma_200:
                market_trend = "BULLISH" # 강세장
            elif latest_market_close < latest_market_sma_200:
                market_trend = "BEARISH" # 약세장
            else:
                market_trend = "NEUTRAL" # 200일선에 걸쳐있을 경우 (드물지만)
        else:
            logger.warning(f"Not enough data for 200-day SMA calculation for {market_index_symbol}. Market trend set to NEUTRAL.")

    logger.info(f"Current Market Trend ({market_index_symbol}): {market_trend}")
    # --- 시장 추세 판단 로직 끝 ---


    # --- 실시간 신호 감지를 위한 데이터 수집 ---
    period_str = '7d' # yfinance 1분봉 최대 기간

    # 모든 종목의 1분봉 데이터를 한 번에 요청
    all_intraday_data_dict = get_ohlcv_data(
        symbols=STOCK_SYMBOLS,
        period=period_str,
        interval=INTRADAY_INTERVAL
    )

    if not isinstance(all_intraday_data_dict, dict) or not all_intraday_data_dict:
        logger.error(f"Failed to fetch any intraday data for all symbols. Expected dictionary, got {type(all_intraday_data_dict)}.")
        return

    # --- 각 종목별 일봉 지표 (피봇/피보나치) 사전 계산 및 저장 ---
    # real-time signal detection에서 지지/저항 수준을 활용하기 위함
    all_daily_extra_indicators = {}
    for symbol in STOCK_SYMBOLS:
        df_daily_for_extras = get_ohlcv_data(
            symbols=symbol,
            period=f"{FIB_LOOKBACK_DAYS}d", # 피보나치 룩백 기간만큼의 일봉 데이터
            interval='1d'
        )
        if not isinstance(df_daily_for_extras, pd.DataFrame) or df_daily_for_extras.empty:
            logger.warning(f"Could not fetch daily data for {symbol} to calculate pivot/fib levels. Skipping for this symbol.")
            all_daily_extra_indicators[symbol] = {} # 빈 딕셔너리로 설정
            continue

        # calculate_daily_indicators는 (df, extra_indicators) 튜플을 반환
        _, extras = calculate_daily_indicators(df_daily_for_extras, FIB_LOOKBACK_DAYS)
        all_daily_extra_indicators[symbol] = extras
    logger.info("Daily pivot/fib levels calculated for all symbols.")
    # --- 각 종목별 일봉 지표 사전 계산 끝 ---


    # 가져온 각 종목의 데이터를 순회하며 처리
    for symbol, df_intraday in all_intraday_data_dict.items():
        # 해당 종목의 일봉 지표 가져오기
        daily_extras_for_symbol = all_daily_extra_indicators.get(symbol, {})
        if not daily_extras_for_symbol:
            logger.warning(f"Skipping signal detection for {symbol}: Daily pivot/fib data not available.")
            continue


        if df_intraday.empty or len(df_intraday) < max(20, 60):
            logger.warning(f"Skipping real-time signal detection for {symbol}: Not enough intraday data available ({len(df_intraday)} rows). Need at least 60 rows for indicators.")
            continue

        df_with_intraday_indicators = calculate_intraday_indicators(df_intraday)

        if df_with_intraday_indicators.empty:
            logger.warning(f"Skipping real-time signal detection for {symbol}: Indicators could not be calculated (DataFrame became empty after dropna).")
            continue

        if len(df_with_intraday_indicators) < 2:
            logger.warning(f"Skipping real-time signal detection for {symbol}: Insufficient intraday data after indicator calculation ({len(df_with_intraday_indicators)} rows).")
            continue

        # 가중치 기반 신호 감지
        # --- market_trend 및 daily_extras_for_symbol 인자 전달 ---
        signal_result = detect_weighted_signals(
            df_with_intraday_indicators,
            symbol,
            market_trend=market_trend, # 시장 추세 전달
            daily_extra_indicators=daily_extras_for_symbol # 일봉 지표 전달
        )
        # --- 인자 전달 끝 ---

        if signal_result:
            latest_data = df_with_intraday_indicators.iloc[-1]
            prev_data = df_with_intraday_indicators.iloc[-2]

            message = format_signal_message(
                ticker=symbol,
                signal_type=signal_result['type'],
                signal_score=signal_result['score'],
                signal_details_list=signal_result['details'],
                current_data=latest_data,
                prev_data=prev_data
            )
            send_telegram_message(message)
        else:
            pass # No strong signal, no message sent
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
