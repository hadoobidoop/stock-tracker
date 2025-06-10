import logging
from time import sleep
from datetime import timedelta, datetime, timezone

import pandas as pd
import yfinance
from pytz import utc

from config import STOCK_SYMBOLS, LOOKBACK_PERIOD_DAYS_FOR_DAILY, INTRADAY_INTERVAL, FIB_LOOKBACK_DAYS, \
    LOOKBACK_PERIOD_DAYS_FOR_INTRADAY, DATA_RETENTION_DAYS
from data_collector import get_ohlcv_data
from database_manager import save_daily_prediction, save_technical_indicators, save_trading_signal, \
    update_stock_metadata, get_stocks_to_analyze, save_intraday_ohlcv, get_intraday_ohlcv_for_analysis, get_db, \
    get_bulk_resampled_ohlcv_from_db
from database_setup import TrendType, IntradayOhlcv, TechnicalIndicator
from indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
from price_predictor import predict_next_day_buy_price
from signal_detector import detect_weighted_signals
from utils import get_current_et_time, is_market_open


# --- [최종 아키텍처] 글로벌 변수를 사용하여 메모리 캐싱 구현 ---
# 이 변수들은 작업이 처음 실행될 때 한 번만 채워지고, 하루 동안 재사용됩니다.
daily_data_cache = {
    "last_updated": None,
    "market_trend": TrendType.NEUTRAL,
    "daily_extras": {},
    "long_term_trends": {},
    "long_term_trend_values": {}
}
logger = logging.getLogger(__name__)


# --- [5단계 수정] 신규 함수: 데이터베이스 유지보수 작업 ---
def run_database_housekeeping_job():
    """
    오래된 데이터를 삭제하여 데이터베이스 크기를 관리하는 유지보수 작업을 실행합니다.
    (intraday_ohlcv, technical_indicators 테이블 대상)
    """
    logger.info("JOB START: Database housekeeping job...")
    db = next(get_db())
    try:
        # 설정 파일에 정의된 보관 기간을 기준으로 삭제 날짜를 계산합니다.
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)
        logger.info(f"Deleting data older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC...")

        # 1. intraday_ohlcv 테이블에서 오래된 데이터 삭제
        ohlcv_deleted_count = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.timestamp_utc < cutoff_date
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {ohlcv_deleted_count} rows from 'intraday_ohlcv'.")

        # 2. technical_indicators 테이블에서 오래된 데이터 삭제
        indicators_deleted_count = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.timestamp_utc < cutoff_date
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {indicators_deleted_count} rows from 'technical_indicators'.")

        db.commit()
        logger.info("JOB END: Database housekeeping job completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred during database housekeeping: {e}")
        db.rollback()
    finally:
        db.close()

def get_long_term_trend(df_hourly: pd.DataFrame) -> tuple[TrendType, dict]:
    """[수정됨] 1시간봉 데이터로 장기 추세를 판단하고, TrendType Enum으로 반환합니다."""
    if df_hourly.empty or len(df_hourly) < 50:
        return TrendType.NEUTRAL, {}

    df_hourly['SMA_50'] = df_hourly['Close'].rolling(window=50).mean()
    last_close = df_hourly.iloc[-1]['Close']
    last_sma = df_hourly.iloc[-1]['SMA_50']
    trend_values = {'close': last_close, 'sma': last_sma}

    if pd.isna(last_sma) or pd.isna(last_close):
        return TrendType.NEUTRAL, trend_values

    if last_close > last_sma:
        return TrendType.BULLISH, trend_values
    elif last_close < last_sma:
        return TrendType.BEARISH, trend_values
    else:
        return TrendType.NEUTRAL, trend_values


def run_daily_buy_price_prediction_job():
    """[최종 수정본] 매일 장 마감 후 실행되는 다음 날 예상 매수 가격 예측 작업 (청킹 적용)"""
    logger.info("JOB START: Daily buy price prediction job...")

    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # --- [신규] 일봉 데이터 요청에도 청킹(Chunking) 로직 적용 ---
    chunk_size = 25
    all_daily_data_dict = {}
    chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]

    logger.info(f"Fetching daily data in {len(chunks)} chunks of size {chunk_size}...")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Fetching daily data for chunk {i + 1}/{len(chunks)}...")
        try:
            chunk_data = get_ohlcv_data(
                symbols=chunk,
                period=f"{LOOKBACK_PERIOD_DAYS_FOR_DAILY}d",
                interval='1d'
            )
            if chunk_data:
                all_daily_data_dict.update(chunk_data)
            sleep(1)  # API 부하 감소
        except Exception as e:
            logger.error(f"Failed to fetch daily data for chunk {i + 1}: {e}")

    if not all_daily_data_dict:
        logger.error("Failed to fetch any daily data. Aborting prediction job.")
        return

    # --- 가져온 데이터를 기반으로 각 종목 분석 ---
    logger.info(f"Starting prediction analysis for {len(all_daily_data_dict)} successfully fetched stocks...")
    current_et = get_current_et_time()

    for symbol, df_daily in all_daily_data_dict.items():
        try:
            if df_daily.empty: continue
            prediction_result = predict_next_day_buy_price(df_daily.copy(), symbol)
            if prediction_result:
                save_daily_prediction({
                    'prediction_date_utc': (current_et + timedelta(days=1)).date(),
                    'generated_at_utc': datetime.now(utc),
                    'ticker': symbol,
                    'prev_day_close': df_daily.iloc[-1]['Close'],
                    **prediction_result
                })
        except Exception as e:
            logger.error(f"An error occurred during prediction analysis for {symbol}: {e}")

    logger.info("JOB END: Daily buy price prediction job completed.")



def run_realtime_signal_detection_job():
    """(최종 검증) 하이브리드 데이터 전략을 사용하여 API 호출을 최소화하고 안정성을 극대화합니다."""
    global daily_data_cache

    current_et = get_current_et_time()


    logger.info("JOB START: Real-time signal detection job...")
    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # --- 1. 최신 분봉 데이터 수집 및 저장 (API 호출) ---
    logger.info("Step 1: Fetching and saving latest intraday OHLCV data...")
    chunk_size = 20
    chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]
    for i, chunk in enumerate(chunks):
        try:
            chunk_data = get_ohlcv_data(chunk, f"{LOOKBACK_PERIOD_DAYS_FOR_INTRADAY}d", INTRADAY_INTERVAL)
            if not chunk_data: continue
            for symbol, df_ohlcv in chunk_data.items():
                if not df_ohlcv.empty: save_intraday_ohlcv(df_ohlcv, symbol)
            sleep(1)
        except Exception as e:
            logger.error(f"Failed to fetch/save raw OHLCV for chunk {i + 1}: {e}")

    # --- 2. 거시적/장기 데이터 준비 (하루에 한 번만 실행되는 캐싱 로직) ---
    if daily_data_cache["last_updated"] != current_et.date():
        logger.info("Step 2: Daily data cache is stale. Refreshing now...")

        # 2.1. 시장 추세 (API 호출)
        try:
            df_market_daily = get_ohlcv_data('^GSPC', "200d", '1d')
            if not df_market_daily.empty and len(df_market_daily) >= 200:
                df_market_daily['SMA_200'] = df_market_daily['Close'].rolling(window=200).mean()
                latest_close = df_market_daily.iloc[-1]['Close']
                latest_sma = df_market_daily.iloc[-1]['SMA_200']
                if not pd.isna(latest_sma):
                    if latest_close > latest_sma: daily_data_cache["market_trend"] = TrendType.BULLISH
                    elif latest_close < latest_sma: daily_data_cache["market_trend"] = TrendType.BEARISH
        except Exception as e:
            logger.error(f"Could not determine market trend: {e}")

        # 2.2. 일봉/시간봉 데이터 일괄 조회 및 처리
        try:
            all_daily_data = get_ohlcv_data(stocks_to_analyze, f"{FIB_LOOKBACK_DAYS}d", '1d')
            all_hourly_data = get_bulk_resampled_ohlcv_from_db(stocks_to_analyze, datetime.now(timezone.utc) - timedelta(days=31), datetime.utcnow(), freq='H')

            for symbol in stocks_to_analyze:
                df_daily = all_daily_data.get(symbol)
                if df_daily is not None and not df_daily.empty:
                    _, extras = calculate_daily_indicators(df_daily, FIB_LOOKBACK_DAYS)
                    daily_data_cache["daily_extras"][symbol] = extras

                df_hourly = all_hourly_data.get(symbol)
                long_term_trend, trend_values = get_long_term_trend(df_hourly)
                daily_data_cache["long_term_trends"][symbol] = long_term_trend
                daily_data_cache["long_term_trend_values"][symbol] = trend_values
        except Exception as e:
            logger.error(f"An error occurred during bulk data fetching for cache: {e}")

        daily_data_cache["last_updated"] = current_et.date()
        logger.info("Daily data cache has been successfully refreshed.")
    else:
        logger.info("Step 2: Using cached daily data.")

    market_trend = daily_data_cache["market_trend"]

    # --- 3. 실시간 분석 및 신호 감지 ---
    logger.info(f"Step 3: Starting signal detection for {len(stocks_to_analyze)} stocks...")
    for symbol in stocks_to_analyze:
        try:
            df_intraday_raw = get_intraday_ohlcv_for_analysis(symbol, LOOKBACK_PERIOD_DAYS_FOR_INTRADAY)
            if df_intraday_raw.empty or len(df_intraday_raw) < 60:
                logger.warning(f"Not enough data for {symbol} in local DB to perform analysis.")
                continue

            # --- [디버깅 로그 추가] ---
            logger.info(f"[{symbol}] 데이터 길이 {len(df_intraday_raw)}로 지표 계산을 시작합니다.")
            logger.info(f"[{symbol}] 전달 직전 데이터 확인 (마지막 3개 행):\n{df_intraday_raw.tail(3).to_string()}")
            # --- [디버깅 로그 끝] ---

            df_with_indicators = calculate_intraday_indicators(df_intraday_raw.copy())
            if df_with_indicators.empty: continue

            indicator_cols_to_drop = ['Open', 'High', 'Low', 'Close', 'Volume']
            df_only_indicators = df_with_indicators.drop(columns=indicator_cols_to_drop, errors='ignore')
            save_technical_indicators(df_only_indicators, symbol, INTRADAY_INTERVAL)

            daily_extras = daily_data_cache["daily_extras"].get(symbol, {})
            long_term_trend = daily_data_cache["long_term_trends"].get(symbol, TrendType.NEUTRAL)
            signal_result = detect_weighted_signals(
                df_with_indicators, symbol, market_trend, long_term_trend, daily_extras
            )

            if signal_result:
                trend_values = daily_data_cache["long_term_trend_values"].get(symbol, {})
                save_trading_signal({
                    'ticker': symbol, 'market_trend': market_trend, 'long_term_trend': long_term_trend,
                    'trend_ref_close': trend_values.get('close'), 'trend_ref_value': trend_values.get('sma'),
                    **signal_result
                })
        except Exception as e:
            logger.error(f"An error occurred during real-time analysis for {symbol}: {e}")

    logger.info("JOB END: Real-time signal detection job completed.")

def update_stock_metadata_from_yfinance():
    """[최종 수정본] yfinance를 사용하여 주식 메타데이터를 가져와 DB를 업데이트합니다. (청킹 적용)"""
    logger.info("JOB START: Updating stock metadata from yfinance...")

    if not STOCK_SYMBOLS:
        logger.warning("STOCK_SYMBOLS list is empty in config.py. Skipping metadata update.")
        return

    chunk_size = 20
    chunks = [STOCK_SYMBOLS[i:i + chunk_size] for i in range(0, len(STOCK_SYMBOLS), chunk_size)]
    metadata_to_save = []

    logger.info(f"Fetching metadata in {len(chunks)} chunks of size {chunk_size}...")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Fetching metadata for chunk {i + 1}/{len(chunks)}...")
        try:
            # yf.Tickers 객체는 여러 티커 정보를 한 번에 요청하는 데 더 효율적입니다.
            tickers_info = yfinance.Tickers(chunk)

            for symbol in chunk:
                # yf.Tickers 객체 내에서 개별 Ticker 객체의 정보에 접근합니다.
                info = tickers_info.tickers[symbol.upper()].info

                if not info or 'symbol' not in info:
                    logger.warning(f"Could not retrieve valid info for {symbol}. Skipping.")
                    continue

                # 데이터 추출 로직은 동일
                metadata = {
                    'ticker': info.get('symbol'),
                    'company_name': info.get('longName'),
                    'exchange': info.get('exchange'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'is_active': not info.get('isDelisted', False),
                    'quote_type': info.get('quoteType'),
                    'currency': info.get('currency'),
                    'market_cap': info.get('marketCap'),
                    'shares_outstanding': info.get('sharesOutstanding'),
                    'beta': info.get('beta'),
                    'dividend_yield': info.get('dividendYield'),
                    'logo_url': info.get('logo_url'),
                    'long_business_summary': info.get('longBusinessSummary')
                }
                metadata_to_save.append(metadata)

            sleep(1)  # 각 청크 요청 후 지연
        except Exception as e:
            logger.error(f"Failed to process metadata for chunk {i + 1}: {e}")
            continue

    if metadata_to_save:
        update_stock_metadata(metadata_to_save)

    logger.info("JOB END: Stock metadata update process finished.")
