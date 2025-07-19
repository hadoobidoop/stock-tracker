"""
전략 조합(Strategy Mix) 설정

여러 정적 전략을 조합하여 신호의 신뢰도와 일관성을 높이는 앙상블 전략 정의
"""

from typing import Dict, Any
from dataclasses import dataclass

from domain.analysis.base.models.enums import StrategyType, StrategyMixMode

@dataclass
class StrategyMixConfig:
    """전략 조합 설정"""
    name: str                           # 조합 이름
    description: str                    # 설명
    mode: StrategyMixMode              # 조합 방식
    strategies: Dict[StrategyType, float]  # 전략별 가중치
    threshold_adjustment: float = 1.0   # 임계값 조정 계수
    
    
# 전략 조합 정의
STRATEGY_MIXES: Dict[str, StrategyMixConfig] = {
    # aggressive_mix는 domain.strategies.aggressive_mix.configs.aggressive_mix_config에서 관리됩니다.
    # conservative_mix는 domain.strategies.conservative_mix.configs.conservative_mix_config에서 관리됩니다.
    # balanced_mix는 domain.strategies.balanced_mix.configs.balanced_mix_config에서 관리됩니다.
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