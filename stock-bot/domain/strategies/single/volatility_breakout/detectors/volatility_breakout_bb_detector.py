from infrastructure.logging import get_logger

logger = get_logger(__name__)

# Volatility Breakout 전략 전용 볼린저밴드(BB) Detector
from domain.signals.detectors.volatility.bb_detector import BBSignalDetector

class VolatilityBreakoutBBDetector(BBSignalDetector):
    """
    Volatility Breakout 전략에 특화된 볼린저밴드 신호 디텍터
    필요시 파라미터/로직 오버라이드 가능
    """
    pass 