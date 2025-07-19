from infrastructure.logging import get_logger

logger = get_logger(__name__)


# Trend Pullback 전략 전용 SMA Detector
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector

class TrendPullbackSMADetector(SMASignalDetector):
    """
    Trend Pullback 전략에 특화된 SMA 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 