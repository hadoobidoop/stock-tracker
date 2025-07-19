"""
전략 조합(Strategy Mix) 모듈

여러 정적 전략을 조합하여 신호의 신뢰도와 일관성을 높이는 앙상블 전략을 제공

책임 분리된 구조:
- models: 데이터 모델 정의
- registry: 전략 조합 레지스트리
- market_conditions: 시장 상황별 전략 관리
- utils: 유틸리티 함수들
"""

# 외부 API - 기존 import 경로와의 호환성 유지
from .models import StrategyMixConfig
from .registry import STRATEGY_MIXES
from .market_conditions import MARKET_CONDITION_STRATEGIES
from .utils import (
    get_strategy_mix_config,
    get_available_strategy_mixes,
    get_market_condition_strategy
)

__all__ = [
    # Models
    'StrategyMixConfig',
    
    # Registry
    'STRATEGY_MIXES',
    
    # Market Conditions
    'MARKET_CONDITION_STRATEGIES',
    
    # Utils
    'get_strategy_mix_config',
    'get_available_strategy_mixes',
    'get_market_condition_strategy',
] 