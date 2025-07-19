import os
from typing import Dict, Any
from domain.signals.models.enums import StrategyMode
from domain.strategies.strategy_config import DefaultStrategyConfig


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
            "dynamic_enabled": DefaultStrategyConfig.dynamic_ENABLED,
            "strategy_mix_enabled": DefaultStrategyConfig.STRATEGY_MIX_ENABLED
        } 