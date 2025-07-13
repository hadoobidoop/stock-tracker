from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals.realtime_signal_settings import VOLUME_SURGE_FACTOR

logger = get_logger(__name__)

# Volatility Breakout 전략 전용 Volume Detector
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector

class VolatilityBreakoutVolumeDetector(VolumeSignalDetector):
    """
    Volatility Breakout 전략에 특화된 거래량 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 