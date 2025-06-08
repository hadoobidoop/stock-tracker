import logging
from asyncio import sleep
from datetime import timedelta, datetime

import pandas as pd
import yfinance
from pytz import utc

from config import STOCK_SYMBOLS, LOOKBACK_PERIOD_DAYS_FOR_DAILY, INTRADAY_INTERVAL, FIB_LOOKBACK_DAYS
from data_collector import get_ohlcv_data
from database_manager import save_daily_prediction, save_technical_indicators, save_trading_signal, \
    update_stock_metadata, get_stocks_to_analyze
from database_setup import TrendType
from indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
from price_predictor import predict_next_day_buy_price
from signal_detector import detect_weighted_signals
from utils import get_current_et_time, is_market_open

logger = logging.getLogger(__name__)


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
    """[최종 수정본] 실시간 신호 감지 작업 (3단계 탑다운 필터링 적용)"""

    # === 1. 사전 준비 (Pre-computation) ===

    current_et = get_current_et_time()
    if not is_market_open(current_et):
        logger.debug(f"Market is closed. Skipping real-time job.")
        return

    logger.info("JOB START: Real-time signal detection job...")

    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # --- 1단계 필터: 총사령관의 전략 방향 (Market Trend) ---
    market_trend = TrendType.NEUTRAL
    df_market_daily = get_ohlcv_data('^GSPC', "200d", '1d')
    if not df_market_daily.empty and len(df_market_daily) >= 200:
        df_market_daily['SMA_200'] = df_market_daily['Close'].rolling(window=200).mean()
        latest_market_close = df_market_daily.iloc[-1]['Close']
        latest_market_sma_200 = df_market_daily.iloc[-1]['SMA_200']
        if not pd.isna(latest_market_sma_200):
            if latest_market_close > latest_market_sma_200:
                market_trend = TrendType.BULLISH
            elif latest_market_close < latest_market_sma_200:
                market_trend = TrendType.BEARISH
        logger.info(f"Filter 1 (Market Trend): {market_trend.value}")

    # --- 2단계 필터: 사단장의 전술적 판단 (Long-term Trend of Stock) ---
    logger.info("Filter 2: Pre-calculating daily indicators and long-term trends...")
    all_daily_extra_indicators = {}
    all_long_term_trends = {}
    all_long_term_trend_values = {}  # [신규] 추세 판단 기준값을 저장할 딕셔너리

    for symbol in stocks_to_analyze:
        df_daily = get_ohlcv_data(symbol, f"{FIB_LOOKBACK_DAYS}d", '1d')
        if not df_daily.empty:
            _, extras = calculate_daily_indicators(df_daily, FIB_LOOKBACK_DAYS)
            all_daily_extra_indicators[symbol] = extras
        else:
            all_daily_extra_indicators[symbol] = {}

        # 1시간봉 데이터로 장기 추세 판단
        df_hourly = get_ohlcv_data(symbol, period="1mo", interval="60m")
        long_term_trend, trend_values = get_long_term_trend(df_hourly)
        all_long_term_trends[symbol] = long_term_trend
        all_long_term_trend_values[symbol] = trend_values  # 기준값 저장

    # --- 5분봉 데이터 수집 (청킹) ---
    chunk_size = 20
    all_intraday_data_dict = {}
    chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]
    for i, chunk in enumerate(chunks):
        try:
            chunk_data = get_ohlcv_data(chunk, '7d', INTRADAY_INTERVAL)
            if chunk_data: all_intraday_data_dict.update(chunk_data)
            sleep(1)
        except Exception as e:
            logger.error(f"Failed to fetch intraday data for chunk {i + 1}: {e}")

    if not all_intraday_data_dict:
        logger.error("Failed to fetch any intraday data. Aborting job.")
        return

    # === 3단계 필터: 현장 지휘관의 실행 명령 (5-min Signal & Score) ===
    logger.info(f"Filter 3: Starting analysis for {len(all_intraday_data_dict)} stocks...")
    for symbol, df_intraday in all_intraday_data_dict.items():
        try:
            if df_intraday.empty or len(df_intraday) < 60: continue

            df_with_indicators = calculate_intraday_indicators(df_intraday.copy())
            if df_with_indicators.empty: continue
            save_technical_indicators(df_with_indicators, symbol, INTRADAY_INTERVAL)

            # 신호 감지 시, 모든 상위 필터 정보 전달
            daily_extras = all_daily_extra_indicators.get(symbol, {})
            long_term_trend = all_long_term_trends.get(symbol, TrendType.NEUTRAL)

            signal_result = detect_weighted_signals(
                df_with_indicators,
                symbol,
                market_trend,  # 1단계 필터 결과
                long_term_trend,  # 2단계 필터 결과
                daily_extras
            )

            if signal_result:
                trend_values = all_long_term_trend_values.get(symbol, {})
                save_trading_signal({
                    'ticker': symbol,
                    'market_trend': market_trend,  # TrendType Enum 전달
                    'long_term_trend': long_term_trend,  # TrendType Enum 전달
                    'trend_ref_close': trend_values.get('close'),
                    'trend_ref_value': trend_values.get('sma'),
                    **signal_result
                })
        except Exception as e:
            logger.error(f"An error occurred during analysis for {symbol}: {e}")

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
