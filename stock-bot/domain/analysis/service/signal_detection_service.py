from typing import Dict, Optional
from ..base.signal_orchestrator import SignalDetectionOrchestrator
from ..detectors.trend_following.sma_detector import SMASignalDetector
from ..detectors.trend_following.macd_detector import MACDSignalDetector
from ..detectors.momentum.rsi_detector import RSISignalDetector
from ..detectors.volume.volume_detector import VolumeSignalDetector
from ..detectors.composite.composite_detector import CompositeSignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_WEIGHTS

class DetectorFactory:
    """신호 감지기 팩토리 클래스"""
    
    @staticmethod
    def create_trend_following_detectors() -> list:
        """추세 추종 감지기들 생성"""
        return [
            SMASignalDetector(SIGNAL_WEIGHTS["golden_cross_sma"]),
            MACDSignalDetector(SIGNAL_WEIGHTS["macd_cross"])
        ]
    
    @staticmethod
    def create_momentum_detectors() -> list:
        """모멘텀 감지기들 생성"""
        return [
            RSISignalDetector(SIGNAL_WEIGHTS["rsi_bounce_drop"])
        ]
    
    @staticmethod
    def create_volume_detectors() -> list:
        """거래량 감지기들 생성"""
        return [
            VolumeSignalDetector(SIGNAL_WEIGHTS["volume_surge"])
        ]
    
    @staticmethod
    def create_composite_detectors() -> list:
        """복합 감지기들 생성"""
        macd_detector = MACDSignalDetector(0)  # 가중치는 복합에서 설정
        volume_detector = VolumeSignalDetector(0)
        
        return [
            CompositeSignalDetector(
                detectors=[macd_detector, volume_detector],
                weight=SIGNAL_WEIGHTS["macd_volume_confirm"],
                require_all=True,
                name="MACD_Volume_Confirm"
            )
        ]
    
    @staticmethod
    def create_default_orchestrator(daily_extra_indicators: Dict = None) -> SignalDetectionOrchestrator:
        """기본 설정된 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 각 카테고리별 감지기 추가
        for detector in DetectorFactory.create_trend_following_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_momentum_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_volume_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_composite_detectors():
            orchestrator.add_detector(detector)
        
        return orchestrator
    
    @staticmethod
    def create_conservative_orchestrator() -> SignalDetectionOrchestrator:
        """보수적 전략용 오케스트레이터"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 높은 신뢰도 감지기만 사용
        orchestrator.add_detector(SMASignalDetector(SIGNAL_WEIGHTS["golden_cross_sma"] * 1.5))
        orchestrator.add_detector(MACDSignalDetector(SIGNAL_WEIGHTS["macd_cross"] * 1.5))
        
        return orchestrator
    
    @staticmethod
    def create_aggressive_orchestrator() -> SignalDetectionOrchestrator:
        """공격적 전략용 오케스트레이터"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 모든 감지기 사용 + 낮은 임계값
        for detector in DetectorFactory.create_trend_following_detectors():
            orchestrator.add_detector(detector)
        for detector in DetectorFactory.create_momentum_detectors():
            orchestrator.add_detector(detector)
        for detector in DetectorFactory.create_volume_detectors():
            orchestrator.add_detector(detector)
        
        return orchestrator