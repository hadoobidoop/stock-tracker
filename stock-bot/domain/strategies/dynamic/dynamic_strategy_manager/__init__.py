"""
Dynamic Strategy Manager Package

This package contains the dynamic strategy management system that handles
dynamic strategy creation, management, and execution.
"""

from .dynamic_strategy_manager import DynamicStrategyManager
from .dynamic_strategy import DynamicCompositeStrategy

__all__ = ['DynamicStrategyManager', 'DynamicCompositeStrategy']
