"""
공통 설정 파일
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum


class StrategyMode(Enum):
    """전략 실행 모드"""
    STATIC = "static"               # 정적 전략 (고정 규칙)
    DYNAMIC = "dynamic"             # 동적 전략 (가중치 조절)
    STATIC_MIX = "static_mix"       # Static Strategy Mix (여러 정적 전략 조합)


def get_available_static_strategies() -> List[str]:
    """동적으로 사용 가능한 정적 전략 목록 조회"""
    try:
        from domain.analysis.config.static_strategies import get_static_strategy_types
        return [st.value.upper() for st in get_static_strategy_types()]
    except ImportError:
        # 폴백: 기본 전략들만
        return ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]


def get_available_dynamic_strategies() -> List[str]:
    """동적으로 사용 가능한 동적 전략 목록 조회"""
    try:
        from domain.analysis.config.dynamic_strategies import get_all_strategies
        return list(get_all_strategies().keys())
    except ImportError:
        # 폴백: 기본 동적 전략들만
        return ["dynamic_weight_strategy", "conservative_dynamic_strategy", "aggressive_dynamic_strategy"]


def get_available_strategy_mix() -> List[str]:
    """사용 가능한 Strategy Mix 목록 조회"""
    return ["balanced_mix", "conservative_mix", "aggressive_mix"]


class DefaultStrategyConfig:
    """기본 전략 설정"""
    
    # === 기본 전략 모드 ===
    DEFAULT_STRATEGY_MODE = StrategyMode.DYNAMIC
    
    # === 정적 전략 설정 ===
    DEFAULT_STATIC_STRATEGY = "BALANCED"  # CONSERVATIVE, BALANCED, AGGRESSIVE
    STATIC_STRATEGIES_ENABLED = True
    
    # === 동적 전략 설정 ===
    DEFAULT_DYNAMIC_STRATEGY = "dynamic_weight_strategy"
    DYNAMIC_STRATEGIES_ENABLED = True
    
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


class EnvironmentConfig:
    """환경별 설정"""
    
    @staticmethod
    def get_strategy_mode() -> StrategyMode:
        """환경변수에서 전략 모드 조회"""
        mode_str = os.getenv("STRATEGY_MODE", DefaultStrategyConfig.DEFAULT_STRATEGY_MODE.value)
        try:
            return StrategyMode(mode_str.lower())
        except ValueError:
            return DefaultStrategyConfig.DEFAULT_STRATEGY_MODE
    
    @staticmethod
    def get_realtime_strategy_config() -> Dict[str, Any]:
        """실시간 작업용 전략 설정 조회"""
        return {
            "mode": EnvironmentConfig.get_strategy_mode(),
            "static_strategy": os.getenv("STATIC_STRATEGY", DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY),
            "dynamic_strategy": os.getenv("DYNAMIC_STRATEGY", DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY),
            "strategy_mix": os.getenv("STRATEGY_MIX", DefaultStrategyConfig.DEFAULT_STRATEGY_MIX),
            "fallback_enabled": os.getenv("STRATEGY_FALLBACK", "true").lower() == "true"
        }
    
    @staticmethod
    def get_backtest_strategy_config() -> Dict[str, Any]:
        """백테스팅용 전략 설정 조회"""
        backtest_mode_str = os.getenv("BACKTEST_STRATEGY_MODE", DefaultStrategyConfig.BACKTEST_DEFAULT_STRATEGY_MODE.value)
        try:
            backtest_mode = StrategyMode(backtest_mode_str.lower())
        except ValueError:
            backtest_mode = DefaultStrategyConfig.BACKTEST_DEFAULT_STRATEGY_MODE
            
        return {
            "mode": backtest_mode,
            "allow_switching": os.getenv("BACKTEST_ALLOW_SWITCHING", "true").lower() == "true",
            "static_strategies_enabled": DefaultStrategyConfig.STATIC_STRATEGIES_ENABLED,
            "dynamic_strategies_enabled": DefaultStrategyConfig.DYNAMIC_STRATEGIES_ENABLED,
            "strategy_mix_enabled": DefaultStrategyConfig.STRATEGY_MIX_ENABLED
        }


def get_strategy_availability() -> Dict[str, Dict[str, Any]]:
    """전략별 활성화 상태 관리 (동적 생성)"""
    return {
        "static_strategies": {
            "enabled": DefaultStrategyConfig.STATIC_STRATEGIES_ENABLED,
            "available": get_available_static_strategies(),
            "default": DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY
        },
        "dynamic_strategies": {
            "enabled": DefaultStrategyConfig.DYNAMIC_STRATEGIES_ENABLED,
            "available": get_available_dynamic_strategies(),
            "default": DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY
        },
        "strategy_mix": {
            "enabled": DefaultStrategyConfig.STRATEGY_MIX_ENABLED,
            "available": get_available_strategy_mix(),
            "default": DefaultStrategyConfig.DEFAULT_STRATEGY_MIX
        }
    }


# 하위 호환성을 위한 전역 변수 (동적 생성)
STRATEGY_AVAILABILITY = get_strategy_availability()
