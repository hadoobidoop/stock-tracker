# MultiTimeframe 전략 config (독립)

from domain.analysis.strategy.configs.static_strategies import StrategyType

MULTI_TIMEFRAME_CONFIG = {
    "name": "다중 시간대 확인 전략",
    "description": "장기 추세(일봉)와 단기(시간봉) 진입 신호를 함께 확인하는 전략",
    "signal_threshold": 9.0,
    "risk_per_trade": 0.02,
    "detector_weights": {
        "macd": 5.0,
        "stoch": 5.0,
        "rsi": 4.0
    },
    "market_filters": {
        "multi_timeframe_confirmation": True
    },
    "position_management": {
        "max_positions": 3,
        "position_timeout_hours": 504
    },
    "strategy_type": StrategyType.MULTI_TIMEFRAME
} 