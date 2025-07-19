"""
Single Strategies Package

This package contains individual trading strategies that operate independently.
Each strategy has its own configuration, detectors, and implementation.
"""

from . import (
    conservative,
    balanced,
    aggressive,
    momentum,
    mean_reversion,
    scalping,
    swing,
    trend_following,
    trend_pullback,
    volatility_breakout,
    multi_timeframe
)

__all__ = [
    'conservative',
    'balanced',
    'aggressive',
    'momentum',
    'mean_reversion',
    'scalping',
    'swing',
    'trend_following',
    'trend_pullback',
    'volatility_breakout',
    'multi_timeframe'
] 