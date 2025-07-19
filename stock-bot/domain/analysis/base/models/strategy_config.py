"""
전략 설정 모델
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .detector_config import DetectorConfig


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    description: str
    signal_threshold: float
    risk_per_trade: float
    implementation_class: Optional[str] = None  # 구현 클래스 경로
    detectors: List[DetectorConfig] = field(default_factory=list)  # 이제 선택 사항
    market_filters: Dict[str, Any] = field(default_factory=dict)
    position_management: Dict[str, Any] = field(default_factory=dict)