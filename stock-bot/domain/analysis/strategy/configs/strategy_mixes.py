"""
전략 조합(Strategy Mix) 설정

여러 정적 전략을 조합하여 신호의 신뢰도와 일관성을 높이는 앙상블 전략 정의
"""

from dataclasses import dataclass
from typing import Dict, Union

from domain.analysis.base.models.enums import StrategyType, StrategyMixMode


@dataclass
class StrategyMixConfig:
    """전략 조합 설정"""
    name: str                           # 조합 이름
    description: str                    # 설명
    mode: StrategyMixMode              # 조합 방식
    strategies: Dict[StrategyType, float]  # 전략별 가중치
    threshold_adjustment: float = 1.0   # 임계값 조정 계수
    
    
# Import individual mix configurations
from domain.strategies.strategy_mixes.aggressive_mix.configs.aggressive_mix_config import AGGRESSIVE_MIX_CONFIG
from domain.strategies.strategy_mixes.conservative_mix.configs.conservative_mix_config import CONSERVATIVE_MIX_CONFIG
from domain.strategies.strategy_mixes.balanced_mix.configs.balanced_mix_config import BALANCED_MIX_CONFIG

# 전략 조합 정의 - 개별 폴더에서 이관된 설정들을 중앙 집중화
# Note: The individual configs have their own dataclass types but compatible interfaces
STRATEGY_MIXES: Dict[str, Union[StrategyMixConfig, object]] = {
    "aggressive_mix": AGGRESSIVE_MIX_CONFIG,
    "conservative_mix": CONSERVATIVE_MIX_CONFIG,
    "balanced_mix": BALANCED_MIX_CONFIG,
}

# 시장 상황별 권장 전략 조합
MARKET_CONDITION_STRATEGIES: Dict[str, Dict[str, str]] = {
    "bullish": {
        "primary": "aggressive_mix",
        "secondary": "balanced_mix", 
        "fallback": "conservative_mix"
    },
    "bearish": {
        "primary": "conservative_mix",
        "secondary": "balanced_mix",
        "fallback": "aggressive_mix"
    },
    "sideways": {
        "primary": "balanced_mix",
        "secondary": "conservative_mix",
        "fallback": "aggressive_mix"
    },
    "high_volatility": {
        "primary": "conservative_mix",
        "secondary": "balanced_mix",
        "fallback": "aggressive_mix"
    },
    "low_volatility": {
        "primary": "aggressive_mix",
        "secondary": "balanced_mix",
        "fallback": "conservative_mix"
    }
}

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