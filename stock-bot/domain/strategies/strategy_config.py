"""
전략 설정 모델
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from domain.signals.detectors.detector_config import DetectorConfig
from domain.signals.models.enums import StrategyMode
from domain.orchestration.strategy_registry import (
    get_available_static_strategies,
    get_available_dynamic_strategies,
    get_available_strategy_mixes
)


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


class DefaultStrategyConfig:
    """기본 전략 설정"""
    # === 기본 전략 모드 ===
    DEFAULT_STRATEGY_MODE = StrategyMode.DYNAMIC
    # === 정적 전략 설정 ===
    DEFAULT_STATIC_STRATEGY = "BALANCED"  # CONSERVATIVE, BALANCED, AGGRESSIVE
    STATIC_STRATEGIES_ENABLED = True
    # === 동적 전략 설정 ===
    DEFAULT_DYNAMIC_STRATEGY = "dynamic_weight_strategy"
    dynamic_ENABLED = True
    # === Static Strategy Mix 설정 ===
    DEFAULT_STRATEGY_MIX = "balanced_mix"  # balanced_mix, conservative_mix, aggressive_mix
    STRATEGY_MIX_ENABLED = True
    # === 백테스팅 기본 설정 ===
    BACKTEST_DEFAULT_STRATEGY_MODE = StrategyMode.DYNAMIC
    BACKTEST_ALLOW_STRATEGY_SWITCHING = True
    # === 실시간 작업 기본 설정 ===
    REALTIME_JOB_STRATEGY_MODE = StrategyMode.DYNAMIC
    REALTIME_JOB_STRATEGY_NAME = "dynamic_weight_strategy"  # 기본 동적 전략
    # === 스케줄러 작업 설정 ===
    SCHEDULER_STRATEGY_FALLBACK_ENABLED = True  # 동적 전략 실패 시 정적 전략으로 폴백
    SCHEDULER_FALLBACK_STATIC_STRATEGY = "BALANCED"

def get_strategy_availability() -> Dict[str, Dict[str, Any]]:
    """전략별 활성화 상태 관리 (동적 생성)"""
    return {
        "static_strategies": {
            "enabled": DefaultStrategyConfig.STATIC_STRATEGIES_ENABLED,
            "available": get_available_static_strategies(),
            "default": DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY
        },
        "dynamic": {
            "enabled": DefaultStrategyConfig.dynamic_ENABLED,
            "available": get_available_dynamic_strategies(),
            "default": DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY
        },
        "strategy_mix": {
            "enabled": DefaultStrategyConfig.STRATEGY_MIX_ENABLED,
            "available": get_available_strategy_mixes(),
            "default": DefaultStrategyConfig.DEFAULT_STRATEGY_MIX
        }
    }

