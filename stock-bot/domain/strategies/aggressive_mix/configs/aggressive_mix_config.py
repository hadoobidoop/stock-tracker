from typing import Dict
from dataclasses import dataclass
from enum import Enum
from domain.analysis.base.models import StrategyType

class StrategyMixMode(Enum):
    WEIGHTED = "weighted"
    VOTING = "voting"
    ENSEMBLE = "ensemble"

@dataclass
class AggressiveMixConfig:
    name: str
    description: str
    mode: StrategyMixMode
    strategies: Dict[StrategyType, float]
    threshold_adjustment: float = 1.0

# aggressive_mix 조합 정의
AGGRESSIVE_MIX_CONFIG = AggressiveMixConfig(
    name="공격적 조합 (Aggressive Mix)",
    description="모멘텀, 스캘핑, 변동성 돌파 전략을 조합하여 빠른 기회 포착",
    mode=StrategyMixMode.WEIGHTED,
    strategies={
        StrategyType.MOMENTUM: 0.4,             # 40% - 모멘텀
        StrategyType.SCALPING: 0.3,             # 30% - 초단기 신호
        StrategyType.VOLATILITY_BREAKOUT: 0.3,  # 30% - 변동성 돌파
    },
    threshold_adjustment=0.8  # 임계값을 낮춰 더 많은 신호 포착
) 