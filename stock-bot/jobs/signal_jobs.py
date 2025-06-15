import logging
from datetime import timedelta, datetime, timezone

import pandas as pd

from ..config import LOOKBACK_PERIOD_DAYS_FOR_INTRADAY, INTRADAY_INTERVAL, FIB_LOOKBACK_DAYS
from ..data_collector import get_ohlcv_data
from ..database_manager import save_technical_indicators, save_trading_signal, get_stocks_to_analyze, \
    get_bulk_resampled_ohlcv_from_db
from ..database_setup import TrendType
from ..database_manager import get_intraday_ohlcv_for_analysis
from ..indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
from ..signal_detector import detect_weighted_signals
from ..utils import get_current_et_time, is_market_open, get_long_term_trend

logger = logging.getLogger(__name__)

# --- [최종 아키텍처] 글로벌 변수를 사용하여 메모리 캐싱 구현 ---
# 이 변수들은 작업이 처음 실행될 때 한 번만 채워지고, 하루 동안 재사용됩니다.
daily_data_cache = {
    "last_updated": None,
    "market_trend": TrendType.NEUTRAL,
    "daily_extras": {},
    "long_term_trends": {},
    "long_term_trend_values": {}
}


def run_realtime_signal_detection_job():
    """하이브리드 데이터 전략을 사용하여 API 호출을 최소화하고 안정성을 극대화합니다."""
    global daily_data_cache

    current_et = get_current_et_time()
    logger.info("JOB START: Real-time signal detection job...")

    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    logger.info("Step 1: Using previously collected intraday OHLCV data...")

    if daily_data_cache["last_updated"] != current_et.date():
        logger.info("Step 2: Refreshing daily data cache...")

        # 2.1. 시장 추세 (API 호출)
        try:
            df_market_daily = get_ohlcv_data('^GSPC', "200d", '1d')
            if not df_market_daily.empty and len(df_market_daily) >= 200:
                df_market_daily['SMA_200'] = df_market_daily['Close'].rolling(window=200).mean()
                latest_close = df_market_daily.iloc[-1]['Close']
                latest_sma = df_market_daily.iloc[-1]['SMA_200']
                if not pd.isna(latest_sma):
                    if latest_close > latest_sma:
                        daily_data_cache["market_trend"] = TrendType.BULLISH
                    elif latest_close < latest_sma:
                        daily_data_cache["market_trend"] = TrendType.BEARISH
        except Exception as e:
            logger.error(f"Could not determine market trend: {e}")

        # 2.2. 일봉/시간봉 데이터 일괄 조회 및 처리
        try:
            all_daily_data = get_ohlcv_data(stocks_to_analyze, f"{FIB_LOOKBACK_DAYS}d", '1d')
            all_hourly_data = get_bulk_resampled_ohlcv_from_db(stocks_to_analyze,
                                                               datetime.now(timezone.utc) - timedelta(days=31),
                                                               datetime.utcnow(), freq='H')

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
