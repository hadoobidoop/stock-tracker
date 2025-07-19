from infrastructure.logging import get_logger

logger = get_logger(__name__)

# Volatility Breakout 전략 전용 Volume Detector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector

class VolatilityBreakoutVolumeDetector(VolumeSignalDetector):
    """
    Volatility Breakout 전략에 특화된 거래량 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 