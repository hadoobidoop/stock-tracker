"""
전략 실행 모드 정의
"""

from enum import Enum


class StrategyMode(Enum):
    """전략 실행 모드"""
    STATIC = "static"               # 정적 전략 (고정 규칙)
    DYNAMIC = "dynamic"             # 동적 전략 (가중치 조절)
    STATIC_MIX = "static_mix"       # Static Strategy Mix (여러 정적 전략 조합)