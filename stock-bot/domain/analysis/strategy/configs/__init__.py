"""
전략 설정 패키지

이 패키지는 정적 전략, 동적 전략, 전략 조합 설정을 관리합니다.
"""

# Deprecated: static_strategies.py is deprecated
# Use individual config classes instead
from .strategy_mixes import *

__all__ = [
    # strategy_mixes
    'StrategyMixMode', 'StrategyMixConfig', 'STRATEGY_MIXES',
    'MARKET_CONDITION_STRATEGIES',
    'get_strategy_mix_config', 'get_available_strategy_mixes',
    'get_market_condition_strategy'
]
