"""
전략 조합(Strategy Mix) 데이터 모델

전략 조합에서 사용되는 기본 데이터 구조들을 정의
"""

from dataclasses import dataclass
from typing import Dict

from domain.signals.models.enums import StrategyType, StrategyMixMode


@dataclass
class StrategyMixConfig:
    """전략 조합 설정"""
    name: str                           # 조합 이름
    description: str                    # 설명
    mode: StrategyMixMode              # 조합 방식
    strategies: Dict[StrategyType, float]  # 전략별 가중치
    threshold_adjustment: float = 1.0   # 임계값 조정 계수 