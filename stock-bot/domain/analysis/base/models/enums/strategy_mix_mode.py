"""
전략 조합 방식 정의
"""

from enum import Enum


class StrategyMixMode(Enum):
    """전략 조합 방식"""
    WEIGHTED = "weighted"    # 가중치 기반 조합
    VOTING = "voting"        # 투표 기반 조합 (과반수)
    ENSEMBLE = "ensemble"    # 앙상블 조합 (신뢰도 기반)