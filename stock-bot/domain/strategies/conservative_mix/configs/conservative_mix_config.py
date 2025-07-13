"""
conservative_mix 전략 조합 config

- CONSERVATIVE, QUALITY_TREND, SWING 전략을 투표 기반(과반수 동의)으로 조합
- mode: StrategyMixMode.VOTING (투표 기반)
- strategies: 각 하위 전략별 가중치(동등, 1.0)
- threshold_adjustment: 1.2 (기본 임계값 8.0 → 9.6)
- name/description: 한글/영문 병기

활용 포인트:
    - 매우 보수적이고 신뢰도 높은 신호만 생성
    - 거짓 신호 최소화, 안정적 거래
    - 각 전략별 근거가 모두 기록되어 설명력/디버깅에 유리
"""
from domain.analysis.strategy.configs.static_strategies import StrategyType
from domain.analysis.strategy.configs.strategy_mixes import StrategyMixMode
from dataclasses import dataclass
from typing import Dict

@dataclass
class ConservativeMixConfig:
    name: str
    description: str
    mode: StrategyMixMode
    strategies: Dict[StrategyType, float]
    threshold_adjustment: float = 1.2

CONSERVATIVE_MIX_CONFIG = ConservativeMixConfig(
    name="보수적 조합 (Conservative Mix)",
    description="여러 추세 및 품질 기반 전략들의 과반수 동의로 안정적인 신호 생성",
    mode=StrategyMixMode.VOTING,
    strategies={
        StrategyType.CONSERVATIVE: 1.0,
        StrategyType.QUALITY_TREND: 1.0,
        StrategyType.SWING: 1.0,
    },
    threshold_adjustment=1.2
) 