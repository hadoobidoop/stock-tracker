from dataclasses import dataclass
from typing import Dict

from domain.signals.models.enums import StrategyType, StrategyMixMode


@dataclass
class BalancedMixConfig:
    name: str
    description: str
    mode: StrategyMixMode
    strategies: Dict[StrategyType, float]
    threshold_adjustment: float = 1.0

# balanced_mix 조합 정의
BALANCED_MIX_CONFIG = BalancedMixConfig(
    name="균형 조합 (Balanced Mix)",
    description="추세추종 전략과 평균 회귀 전략을 조합하여 다양한 시장 상황에 대응",
    mode=StrategyMixMode.WEIGHTED,
    strategies={
        StrategyType.TREND_FOLLOWING: 0.5,  # 50% - 추세 추종
        StrategyType.MEAN_REVERSION: 0.5,   # 50% - 평균 회귀
    },
    threshold_adjustment=1.0  # 기본 임계값
) 