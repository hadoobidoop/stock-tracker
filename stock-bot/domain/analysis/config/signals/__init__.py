"""
신호 설정 패키지

이 패키지는 신호 감지, 분석, 조정 관련 설정을 관리합니다.
"""

from .realtime_signal_settings import *
from .signal_weights import *
from .signal_adjustment_factors import *
from .prediction_signal_settings import *

__all__ = [
    # realtime_signal_settings
    'COLLECTION_INTERVAL_MINUTES', 'INTRADAY_INTERVAL', 
    'LOOKBACK_PERIOD_DAYS_FOR_DAILY', 'LOOKBACK_PERIOD_MINUTES_FOR_INTRADAY',
    'VOLUME_SURGE_FACTOR', 'REALTIME_SIGNAL_DETECTION',
    # signal_weights
    'SIGNAL_WEIGHTS', 'SIGNAL_THRESHOLD',
    # signal_adjustment_factors
    'SIGNAL_ADJUSTMENT_FACTORS_BY_TREND',
    # prediction_signal_settings
    'DAILY_PREDICTION_HOUR_ET', 'DAILY_PREDICTION_MINUTE_ET',
    'PREDICTION_ATR_MULTIPLIER_FOR_RANGE', 'PREDICTION_SIGNAL_WEIGHTS',
    'PREDICTION_THRESHOLD'
]
