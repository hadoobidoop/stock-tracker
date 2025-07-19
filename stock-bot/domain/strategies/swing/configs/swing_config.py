from domain.analysis.base.models import StrategyConfig
from dataclasses import dataclass, field
from typing import Dict, Any

SWING_STRATEGY_CONFIG = {
    "name": "스윙 전략",
    "description": "중기 추세 변화를 포착하는 전략",
    "signal_threshold": 7.0,
    "risk_per_trade": 0.025,
    "detector_weights": {
        'sma': 5.0,
        'macd': 6.0,
        'rsi': 4.0,
        'adx': 4.0
    },
    "market_filters": {
        'trend_alignment': False
    },
    "position_management": {
        'max_positions': 3,
        'position_timeout_hours': 336
    }
} 