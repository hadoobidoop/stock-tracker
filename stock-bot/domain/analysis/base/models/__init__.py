"""
공통 모델 정의
"""

from domain.analysis.detectors.detector_config import DetectorConfig
from .enums import StrategyType
# from domain.strategies.strategy_config import StrategyConfig

__all__ = [
    'StrategyType',
    'DetectorConfig',
    'StrategyConfig'
]