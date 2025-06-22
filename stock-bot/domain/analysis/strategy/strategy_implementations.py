"""
구체적인 전략 구현체들

각 전략은 BaseStrategy를 상속받아 고유한 신호 감지 로직을 구현합니다.
"""

from typing import Dict, Any
import importlib

from .base_strategy import BaseStrategy
from domain.analysis.config.strategy_settings import StrategyType, StrategyConfig
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator


class ConservativeStrategy(BaseStrategy):
    """보수적 전략 - 높은 신뢰도의 강한 신호만 사용"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.CONSERVATIVE
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """보수적 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 감지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class BalancedStrategy(BaseStrategy):
    """균형잡힌 전략 - 다양한 신호를 균형있게 사용"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.BALANCED
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """균형잡힌 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class AggressiveStrategy(BaseStrategy):
    """공격적 전략 - 낮은 임계값으로 많은 거래 기회 포착"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.AGGRESSIVE
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """공격적 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class MomentumStrategy(BaseStrategy):
    """모멘텀 전략 - RSI, 스토캐스틱 등 모멘텀 지표 중심"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """모멘텀 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class TrendFollowingStrategy(BaseStrategy):
    """추세추종 전략 - SMA, MACD, ADX 등 추세 지표 중심"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.TREND_FOLLOWING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """추세추종 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class ContrarianStrategy(BaseStrategy):
    """역투자 전략 - 과매수/과매도 구간에서 반대 방향 진입"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.CONTRARIAN
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """역투자 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class ScalpingStrategy(BaseStrategy):
    """스캘핑 전략 - 빠른 진입/청산을 위한 단기 전략"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.SCALPING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """스캘핑 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


class SwingStrategy(BaseStrategy):
    """스윙 전략 - 며칠간 보유하는 중기 전략"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.SWING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """스윙 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator


# 전략 팩토리 클래스
class StrategyFactory:
    """전략 팩토리 - 전략 타입에 따라 적절한 전략 인스턴스 생성"""
    
    _strategy_classes = {
        StrategyType.CONSERVATIVE: ConservativeStrategy,
        StrategyType.BALANCED: BalancedStrategy,
        StrategyType.AGGRESSIVE: AggressiveStrategy,
        StrategyType.MOMENTUM: MomentumStrategy,
        StrategyType.TREND_FOLLOWING: TrendFollowingStrategy,
        StrategyType.CONTRARIAN: ContrarianStrategy,
        StrategyType.SCALPING: ScalpingStrategy,
        StrategyType.SWING: SwingStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: StrategyConfig) -> BaseStrategy:
        """전략 인스턴스를 생성합니다."""
        strategy_class = cls._strategy_classes.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"지원하지 않는 전략 타입: {strategy_type}")
        
        try:
            return strategy_class(strategy_type, config)
        except Exception as e:
            raise RuntimeError(f"전략 생성 실패 {strategy_type}: {e}")
    
    @classmethod
    def get_available_strategies(cls) -> list[StrategyType]:
        """사용 가능한 전략 타입 목록을 반환합니다."""
        return list(cls._strategy_classes.keys())
    
    @classmethod
    def create_multiple_strategies(cls, strategy_configs: Dict[StrategyType, StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """여러 전략을 동시에 생성합니다."""
        strategies = {}
        for strategy_type, config in strategy_configs.items():
            try:
                strategies[strategy_type] = cls.create_strategy(strategy_type, config)
            except Exception as e:
                print(f"전략 생성 실패 {strategy_type}: {e}")
        
        return strategies 