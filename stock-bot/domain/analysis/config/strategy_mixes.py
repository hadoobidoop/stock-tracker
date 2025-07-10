"""
전략 조합(Strategy Mix) 설정

여러 정적 전략을 조합하여 신호의 신뢰도와 일관성을 높이는 앙상블 전략 정의
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

from domain.analysis.config.static_strategies import StrategyType


class StrategyMixMode(Enum):
    """전략 조합 방식"""
    WEIGHTED = "weighted"    # 가중치 기반 조합
    VOTING = "voting"        # 투표 기반 조합 (과반수)
    ENSEMBLE = "ensemble"    # 앙상블 조합 (신뢰도 기반)


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
    
    # 보수적 조합: 안정적인 추세 추종
    "conservative_mix": StrategyMixConfig(
        name="보수적 조합 (Conservative Mix)",
        description="여러 추세 및 품질 기반 전략들의 만장일치로 안정적인 신호 생성",
        mode=StrategyMixMode.VOTING,
        strategies={
            StrategyType.CONSERVATIVE: 1.0,
            StrategyType.TREND_FOLLOWING: 1.0,
        },
        threshold_adjustment=1.2  # 임계값을 높여 더 엄격한 신호 필터링
    ),

    # 균형 조합: 추세와 평균 회귀의 조화
    "balanced_mix": StrategyMixConfig(
        name="균형 조합 (Balanced Mix)",
        description="추세추종 전략과 평균 회귀 전략을 조합하여 다양한 시장 상황에 대응",
        mode=StrategyMixMode.WEIGHTED,
        strategies={
            StrategyType.TREND_FOLLOWING: 0.5,  # 50% - 추세 추종
            StrategyType.MEAN_REVERSION: 0.5,   # 50% - 평균 회귀
        },
        threshold_adjustment=1.0  # 기본 임계값
    ),
    
    # 공격적 조합: 빠른 신호 및 변동성 포착
    "aggressive_mix": StrategyMixConfig(
        name="공격적 조합 (Aggressive Mix)",
        description="모멘텀, 스캘핑, 변동성 돌파 전략을 조합하여 빠른 기회 포착",
        mode=StrategyMixMode.WEIGHTED,
        strategies={
            StrategyType.MOMENTUM: 0.4,             # 40% - 모멘텀
            StrategyType.SCALPING: 0.3,             # 30% - 초단기 신호
            StrategyType.VOLATILITY_BREAKOUT: 0.3,  # 30% - 변동성 돌파
        },
        threshold_adjustment=0.8  # 임계값을 낮춰 더 많은 신호 포착
    ),
    
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