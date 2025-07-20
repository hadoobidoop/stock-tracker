"""
Signals Analysis Package

이 패키지는 복합 지표 분석 로직을 제공합니다.
각 모듈은 성격에 따라 분리되어 재사용 가능한 분석 함수들을 포함합니다.

모듈:
- momentum.py: RSI, Stoch, MACD 조합 모멘텀 분석 ✅
- trend.py: SMA, MACD, ADX 추세 분석 ✅
- volume.py: MACD와 거래량 조합 분석 ✅
- volatility.py: BB, ADX 변동성 분석 ✅
- multi_timeframe.py: 다중 시간대 분석 ✅
"""

from . import momentum
from . import multi_timeframe
from . import trend
from . import volatility
from . import volume
# 주요 함수들을 직접 import
from .momentum import get_momentum_consensus, analyze_rsi_stoch_condition
from .trend import analyze_macd_cross, analyze_sma_trend, get_trend_strength
from .volatility import analyze_bb_volatility, analyze_adx_trend, get_volatility_pattern
from .volume import analyze_macd_with_volume, get_volume_pattern

__all__ = [
    'momentum',
    'trend', 
    'volume',
    'volatility',
    'multi_timeframe',
    # 직접 사용 가능한 함수들
    'get_momentum_consensus',
    'analyze_rsi_stoch_condition',
    'analyze_macd_cross',
    'analyze_sma_trend', 
    'get_trend_strength',
    'analyze_macd_with_volume',
    'get_volume_pattern',
    'analyze_bb_volatility',
    'analyze_adx_trend',
    'get_volatility_pattern'
] 