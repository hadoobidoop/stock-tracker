"""
탐지기 설정 모델
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DetectorConfig:
    """신호 탐지기 설정"""
    detector_class: str
    weight: float
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}