# Volatility Breakout 전략 config

VOLATILITY_BREAKOUT_BB_WEIGHT = 7.0
VOLATILITY_BREAKOUT_BB_TYPE = "breakout"
VOLATILITY_BREAKOUT_ADX_WEIGHT = 4.0
VOLATILITY_BREAKOUT_VOLUME_WEIGHT = 5.0

DETECTOR_CONFIGS = [
    {"detector_class": "VolatilityBreakoutBBDetector", "weight": VOLATILITY_BREAKOUT_BB_WEIGHT, "detector_type": VOLATILITY_BREAKOUT_BB_TYPE},
    {"detector_class": "VolatilityBreakoutADXDetector", "weight": VOLATILITY_BREAKOUT_ADX_WEIGHT},
    {"detector_class": "VolatilityBreakoutVolumeDetector", "weight": VOLATILITY_BREAKOUT_VOLUME_WEIGHT},
] 