# MultiTimeframeMACDDetector
# - 다중 시간대 전략에서 MACD 신호 감지를 담당하는 래퍼 클래스
# - 추후 커스텀 로직 확장/오버라이드 용이하도록 별도 래퍼로 분리
# - 기본 MACDSignalDetector의 기능을 그대로 상속하며, 가중치만 전달

from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector

class MultiTimeframeMACDDetector(MACDSignalDetector):
    """
    다중 시간대 전략(MultiTimeframeStrategy)에서 MACD 신호 감지를 담당하는 래퍼 Detector.
    - 기본 MACDSignalDetector를 상속하며, 가중치(weight)만 전달
    - 추후 다중 시간대 특화 로직/파라미터 확장 시 이 클래스를 오버라이드하여 사용
    """
    def __init__(self, weight: float):
        """
        Args:
            weight (float): MACD 신호의 가중치
        """
        super().__init__(weight) 