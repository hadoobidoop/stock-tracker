from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals.signal_weights import SIGNAL_WEIGHTS

logger = get_logger(__name__)

# Volatility Breakout 전략 전용 ADX Detector
from domain.analysis.detectors.trend_following.adx_detector import ADXSignalDetector

class VolatilityBreakoutADXDetector(ADXSignalDetector):
    """
    Volatility Breakout 전략에 특화된 ADX 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 