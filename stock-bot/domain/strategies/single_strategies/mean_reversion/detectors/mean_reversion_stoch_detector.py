"""
mean_reversion 전략 전용 StochSignalDetector 래퍼
- 추후 mean_reversion 특화 로직 확장 가능
"""
from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector

class MeanReversionStochSignalDetector(StochSignalDetector):
    def __init__(self, weight: float = 3.0):
        """
        mean_reversion 전략 전용 StochSignalDetector
        Args:
            weight (float): 가중치
        """
        super().__init__(weight=weight) 