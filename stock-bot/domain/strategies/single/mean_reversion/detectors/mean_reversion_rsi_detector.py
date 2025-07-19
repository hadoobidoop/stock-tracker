"""
mean_reversion 전략 전용 RSISignalDetector 래퍼
- 추후 mean_reversion 특화 로직 확장 가능
"""
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector

class MeanReversionRSISignalDetector(RSISignalDetector):
    def __init__(self, weight: float = 4.0):
        """
        mean_reversion 전략 전용 RSISignalDetector
        Args:
            weight (float): 가중치
        """
        super().__init__(weight=weight) 