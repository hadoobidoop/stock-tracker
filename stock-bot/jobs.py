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

