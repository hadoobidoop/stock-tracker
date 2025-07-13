"""
mean_reversion 전략 전용 BBSignalDetector 래퍼
- detector_type="mean_reversion"을 기본값으로 고정
- 추후 mean_reversion 특화 로직 확장 가능
"""
from domain.analysis.detectors.volatility.bb_detector import BBSignalDetector

class MeanReversionBBSignalDetector(BBSignalDetector):
    def __init__(self, weight: float = 6.0, detector_type: str = "mean_reversion"):
        """
        mean_reversion 전략 전용 BBSignalDetector
        Args:
            weight (float): 가중치
            detector_type (str): 디텍터 타입(기본값: mean_reversion)
        """
        super().__init__(weight=weight, detector_type=detector_type) 