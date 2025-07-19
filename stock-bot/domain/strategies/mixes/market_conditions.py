"""
시장 상황별 전략 조합 관리

시장 상황에 따른 권장 전략 조합을 정의하고 관리
"""

from typing import Dict


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