"""
전략 조합(Strategy Mix) 유틸리티 함수

전략 조합과 관련된 헬퍼 함수들을 제공
"""

from typing import Dict

from .models import StrategyMixConfig
from .registry import STRATEGY_MIXES
from .market_conditions import MARKET_CONDITION_STRATEGIES


def get_strategy_mix_config(mix_name: str) -> StrategyMixConfig:
    """전략 조합 설정 조회"""
    return STRATEGY_MIXES.get(mix_name)


def get_available_strategy_mixes() -> Dict[str, StrategyMixConfig]:
    """사용 가능한 전략 조합 목록"""
    return STRATEGY_MIXES.copy()


def get_market_condition_strategy(condition: str, priority: str = "primary") -> str:
    """시장 상황별 권장 전략 조합 조회"""
    condition_strategies = MARKET_CONDITION_STRATEGIES.get(condition, {})
    return condition_strategies.get(priority, "balanced_mix") 