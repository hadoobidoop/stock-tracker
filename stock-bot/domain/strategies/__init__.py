"""
Trading Strategies Package

This package contains all trading strategies organized into three main categories:
1. Single Strategies: Individual strategies that operate independently
2. Strategy Mixes: Combinations of multiple strategies using different methods
3. Dynamic Strategies: Strategies that adapt to market conditions

Structure:
- single_strategies/: Individual trading strategies
- strategy_mixes/: Strategy combinations (weighted, voting, ensemble)
- dynamic_strategies/: Market-adaptive strategies
"""

from . import single_strategies, strategy_mixes, dynamic_strategies

__all__ = [
    'single_strategies',
    'strategy_mixes', 
    'dynamic_strategies'
]
