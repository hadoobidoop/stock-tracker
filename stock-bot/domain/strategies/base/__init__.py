"""
전략 기본 모듈 - 모든 전략이 상속받는 기본 클래스와 유틸리티들

하위 호환성을 위해 기존 import 경로를 유지합니다:
- from domain.strategies.base import BaseStrategy
"""

from .base_strategy import BaseStrategy
from .performance_mixin import PerformanceMixin
from .signal_factory import TradingSignalFactory, TradingSignalMixin

# 완전한 BaseStrategy 구현을 위한 조합 클래스
class FullBaseStrategy(BaseStrategy, PerformanceMixin, TradingSignalMixin):
    """
    모든 기능이 포함된 완전한 BaseStrategy 구현
    기존 코드와의 호환성을 위해 제공
    """
    
    def __init__(self, strategy_type, config):
        # 모든 Mixin과 BaseStrategy 초기화
        super().__init__(strategy_type, config)

# 하위 호환성을 위해 기본 BaseStrategy를 FullBaseStrategy로 교체
BaseStrategy = FullBaseStrategy

__all__ = [
    'BaseStrategy',
    'PerformanceMixin', 
    'TradingSignalFactory',
    'TradingSignalMixin'
]