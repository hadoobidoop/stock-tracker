from infrastructure.logging import get_logger

logger = get_logger(__name__)

# Trend Pullback 전략 전용 RSI Detector
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector

class TrendPullbackRSIDetector(RSISignalDetector):
    """
    Trend Pullback 전략에 특화된 RSI 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 