"""
통합 전략 구현체 (정적/동적 전략 모두 지원)

모든 전략을 통합 관리하며, 확장성과 유지보수성을 고려한 설계
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, StrategyResult
from domain.analysis.config.static_strategies import StrategyType, StrategyConfig, get_strategy_config
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class UniversalStrategy(BaseStrategy):
    """범용 전략 - 모든 정적 전략 타입을 지원하는 통합 클래스"""
    
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.strategy_type = strategy_type
        
    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략 설정에 따른 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 감지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """전략별 점수 조정 (전략 타입에 따라 다른 로직 적용)"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 전략별 특화 로직
        if self.strategy_type == StrategyType.CONSERVATIVE:
            # 보수적 전략: 더 높은 임계값 요구
            adjusted_score *= 0.8
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 0.6
                
        elif self.strategy_type == StrategyType.AGGRESSIVE:
            # 공격적 전략: 더 낮은 임계값 허용
            adjusted_score *= 1.2
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.3
                
        elif self.strategy_type == StrategyType.MOMENTUM:
            # 모멘텀 전략: 추세 방향성 강화
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.15
            elif market_trend == TrendType.BEARISH:
                adjusted_score *= 0.9
                
        elif self.strategy_type == StrategyType.CONTRARIAN:
            # 역추세 전략: 추세와 반대 방향 강화
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 1.2  # 하락장에서 매수 신호 강화
            elif market_trend == TrendType.BULLISH:
                adjusted_score *= 0.8  # 상승장에서 매수 신호 약화
                
        elif self.strategy_type in [StrategyType.TREND_FOLLOWING, StrategyType.TREND_PULLBACK, StrategyType.QUALITY_TREND]:
            # 추세 기반 전략들: 추세 방향 확인 필요
            if market_trend == long_term_trend:
                adjusted_score *= 1.1  # 단기/장기 추세 일치 시 강화
            else:
                adjusted_score *= 0.9  # 추세 불일치 시 약화
                
        elif self.strategy_type == StrategyType.SCALPING:
            # 스캘핑 전략: 변동성이 높을 때 활성화
            # 실제로는 VIX 등 변동성 지표를 확인해야 하지만, 여기서는 단순화
            adjusted_score *= 1.1
            
        elif self.strategy_type in [StrategyType.MEAN_REVERSION, StrategyType.SWING]:
            # 평균 회귀/스윙 전략: 횡보장에서 유리
            if market_trend == TrendType.NEUTRAL:
                adjusted_score *= 1.15
                
        # 다중 시간대와 거시지표 기반 전략은 기본 로직 사용
        
        return adjusted_score


class StrategyFactory:
    """
    통합 전략 팩토리 - 모든 정적 전략과 동적 전략 지원
    
    개선 사항:
    1. 모든 확장된 정적 전략 지원
    2. 동적 전략 생성 기능 추가
    3. 중복 경고 메시지 제거
    4. 설정 기반 전략 생성
    """
    
    @classmethod
    def create_static_strategy(cls, strategy_type: StrategyType, config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """정적 전략 인스턴스 생성"""
        if config is None:
            config = get_strategy_config(strategy_type)
            
        if config is None:
            logger.error(f"전략 설정을 찾을 수 없습니다: {strategy_type.value}")
            return None
            
        try:
            # 모든 정적 전략을 UniversalStrategy로 생성
            strategy = UniversalStrategy(strategy_type, config)
            logger.info(f"정적 전략 생성 성공: {strategy_type.value}")
            return strategy
            
        except Exception as e:
            logger.error(f"정적 전략 생성 실패 {strategy_type.value}: {e}")
            return None
    
    @classmethod
    def create_dynamic_strategy(cls, strategy_name: str) -> Optional[BaseStrategy]:
        """동적 전략 인스턴스 생성"""
        try:
            from .dynamic_strategy import DynamicCompositeStrategy
            strategy = DynamicCompositeStrategy(strategy_name)
            logger.info(f"동적 전략 생성 성공: {strategy_name}")
            return strategy
            
        except Exception as e:
            logger.error(f"동적 전략 생성 실패 {strategy_name}: {e}")
            return None
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """전략 인스턴스 생성 (하위 호환성 유지)"""
        return cls.create_static_strategy(strategy_type, config)
    
    @classmethod
    def get_available_static_strategies(self) -> list[StrategyType]:
        """사용 가능한 정적 전략 목록 반환"""
        from domain.analysis.config.static_strategies import get_static_strategy_types
        return get_static_strategy_types()
    
    @classmethod
    def get_available_dynamic_strategies(self) -> list[str]:
        """사용 가능한 동적 전략 목록 반환"""
        try:
            from domain.analysis.config.dynamic_strategies import get_all_strategies
            return list(get_all_strategies().keys())
        except ImportError:
            return []
    
    @classmethod
    def is_strategy_supported(cls, strategy_identifier: str) -> tuple[bool, str]:
        """전략 지원 여부 확인"""
        # 정적 전략 확인
        try:
            strategy_type = StrategyType(strategy_identifier.lower())
            if get_strategy_config(strategy_type) is not None:
                return True, "static"
        except ValueError:
            pass
        
        # 동적 전략 확인
        try:
            from domain.analysis.config.dynamic_strategies import get_strategy_definition
            if get_strategy_definition(strategy_identifier) is not None:
                return True, "dynamic"
        except ImportError:
            pass
        
        return False, "none"
    
    @classmethod
    def create_multiple_strategies(cls, strategy_configs: Dict[StrategyType, StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """여러 정적 전략 동시 생성"""
        strategies = {}
        for strategy_type, config in strategy_configs.items():
            strategy = cls.create_static_strategy(strategy_type, config)
            if strategy:
                strategies[strategy_type] = strategy
            else:
                logger.warning(f"전략 생성 실패로 건너뜀: {strategy_type.value}")
        return strategies 