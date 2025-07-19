# MultiTimeframeMACDDetector (다중 시간대 MACD 래퍼 Detector)
# =========================================================
# - MultiTimeframeStrategy에서 MACD 신호 감지를 별도 관리/확장/오버라이드 용도로 래핑한 클래스
# - 기본 MACDSignalDetector의 기능을 그대로 상속하며, 가중치만 전달(로직은 동일)
# - 향후 다중 시간대 특화 로직/파라미터/오버라이드가 필요할 때 이 클래스를 확장해 사용
# - 전략 구조의 일관성, 확장성, 유지보수성을 높이기 위한 래퍼 구조

from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector

class MultiTimeframeMACDDetector(MACDSignalDetector):
    """
    MultiTimeframeStrategy에서 MACD 신호 감지를 담당하는 래퍼 Detector.
    - 기본 MACDSignalDetector를 상속하며, 가중치(weight)만 전달
    - 향후 다중 시간대 특화 로직/파라미터/오버라이드가 필요할 때 이 클래스를 확장해 사용
    """
    def __init__(self, weight: float):
        """
        Args:
            weight (float): MACD 신호의 가중치
        """
        super().__init__(weight) 