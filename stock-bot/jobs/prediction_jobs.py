import logging
from datetime import timedelta, datetime, timezone

import pandas as pd
from pytz import utc

from ..database_manager import save_daily_prediction, get_stocks_to_analyze, get_bulk_resampled_ohlcv_from_db
from ..database_setup import TrendType
from ..price_predictor import predict_next_day_buy_price
from ..utils import get_current_et_time, get_long_term_trend

logger = logging.getLogger(__name__)

def run_daily_buy_price_prediction_job():
    """매일 장 마감 후 실행되는 다음 날 예상 매수 가격 예측 작업 (장기 추세 필터링 적용)"""
    logger.info("JOB START: Daily buy price prediction job with trend filter...")

    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    long_term_trends = {}
    try:
        all_hourly_data = get_bulk_resampled_ohlcv_from_db(
            stocks_to_analyze,
            datetime.now(timezone.utc) - timedelta(days=31),
            datetime.now(timezone.utc),
            freq='H'
        )
        for symbol, df_hourly in all_hourly_data.items():
            trend, _ = get_long_term_trend(df_hourly)
            long_term_trends[symbol] = trend
            logger.debug(f"Determined long-term trend for {symbol}: {trend.value}")
    except Exception as e:
        logger.error(f"Failed to determine long-term trends for prediction job: {e}")
        return

    chunk_size = 25
    all_daily_data_dict = {}
    chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]
    logger.info(f"Fetching daily data in {len(chunks)} chunks of size {chunk_size}...")
    current_et = get_current_et_time()

    for symbol, df_daily in all_daily_data_dict.items():
        try:
            symbol_trend = long_term_trends.get(symbol, TrendType.NEUTRAL)

            if symbol_trend == TrendType.BEARISH:
                logger.info(f"Skipping prediction for {symbol} due to BEARISH long-term trend.")
                continue

            if df_daily.empty: continue

            prediction_result = predict_next_day_buy_price(df_daily.copy(), symbol, long_term_trend=symbol_trend)

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