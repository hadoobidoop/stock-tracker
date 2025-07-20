"""
Trend Rules Module

추세 지표(SMA, MACD, ADX) 기반 거래 규칙들을 정의합니다.
analysis.trend 모듈의 함수들을 활용하여 재사용 가능한 규칙을 제공합니다.
"""

import pandas as pd
from typing import Callable

from ..analysis.trend import (
    analyze_macd_cross,
    get_sma_trend_alignment,
    analyze_trend_strength,
    MacdEvidence,
    SMAAlignment,
    TrendStrength
)


def macd_confirms_golden_cross(data: pd.DataFrame) -> bool:
    """MACD 골든크로스 확인 규칙"""
    evidence = analyze_macd_cross(data)
    return evidence == MacdEvidence.GOLDEN_CROSS


def macd_confirms_dead_cross(data: pd.DataFrame) -> bool:
    """MACD 데드크로스 확인 규칙"""
    evidence = analyze_macd_cross(data)
    return evidence == MacdEvidence.DEAD_CROSS


def macd_zero_line_bullish_cross(data: pd.DataFrame) -> bool:
    """MACD 0선 상향 돌파 확인 규칙"""
    evidence = analyze_macd_cross(data)
    return evidence == MacdEvidence.ZERO_LINE_BULLISH_CROSS


def macd_zero_line_bearish_cross(data: pd.DataFrame) -> bool:
    """MACD 0선 하향 돌파 확인 규칙"""
    evidence = analyze_macd_cross(data)
    return evidence == MacdEvidence.ZERO_LINE_BEARISH_CROSS


def sma_bullish_alignment(data: pd.DataFrame) -> bool:
    """SMA 상승 정배열 확인 규칙"""
    alignment = get_sma_trend_alignment(data)
    return alignment == SMAAlignment.BULLISH_ALIGNMENT


def sma_bearish_alignment(data: pd.DataFrame) -> bool:
    """SMA 하락 정배열 확인 규칙"""
    alignment = get_sma_trend_alignment(data)
    return alignment == SMAAlignment.BEARISH_ALIGNMENT


def sma_bullish_cross(data: pd.DataFrame) -> bool:
    """SMA 골든크로스 확인 규칙"""
    alignment = get_sma_trend_alignment(data)
    return alignment == SMAAlignment.BULLISH_CROSS


def sma_bearish_cross(data: pd.DataFrame) -> bool:
    """SMA 데드크로스 확인 규칙"""
    alignment = get_sma_trend_alignment(data)
    return alignment == SMAAlignment.BEARISH_CROSS


def strong_uptrend_confirmed(data: pd.DataFrame) -> bool:
    """강한 상승 추세 확인 규칙"""
    strength = analyze_trend_strength(data)
    return strength == TrendStrength.STRONG_UPTREND


def strong_downtrend_confirmed(data: pd.DataFrame) -> bool:
    """강한 하락 추세 확인 규칙"""
    strength = analyze_trend_strength(data)
    return strength == TrendStrength.STRONG_DOWNTREND


def moderate_uptrend_confirmed(data: pd.DataFrame) -> bool:
    """보통 상승 추세 확인 규칙"""
    strength = analyze_trend_strength(data)
    return strength in [TrendStrength.STRONG_UPTREND, TrendStrength.MODERATE_UPTREND]


def moderate_downtrend_confirmed(data: pd.DataFrame) -> bool:
    """보통 하락 추세 확인 규칙"""
    strength = analyze_trend_strength(data)
    return strength in [TrendStrength.STRONG_DOWNTREND, TrendStrength.MODERATE_DOWNTREND]


def sma_golden_cross_with_trend(data: pd.DataFrame,
                               sma_short_column: str = 'SMA_5',
                               sma_long_column: str = 'SMA_20',
                               adx_column: str = 'ADX_14') -> bool:
    """SMA 골든크로스와 강한 추세 동시 확인"""
    if len(data) < 2:
        return False
    
    required_columns = [sma_short_column, sma_long_column, adx_column]
    if not all(col in data.columns for col in required_columns):
        return False
    
    current_short = data[sma_short_column].iloc[-1]
    current_long = data[sma_long_column].iloc[-1]
    prev_short = data[sma_short_column].iloc[-2]
    prev_long = data[sma_long_column].iloc[-2]
    current_adx = data[adx_column].iloc[-1]
    
    # 골든크로스 발생 + ADX 강세
    golden_cross = prev_short <= prev_long and current_short > current_long
    strong_trend = current_adx >= 25
    
    return golden_cross and strong_trend


def sma_dead_cross_with_trend(data: pd.DataFrame,
                             sma_short_column: str = 'SMA_5',
                             sma_long_column: str = 'SMA_20',
                             adx_column: str = 'ADX_14') -> bool:
    """SMA 데드크로스와 강한 추세 동시 확인"""
    if len(data) < 2:
        return False
    
    required_columns = [sma_short_column, sma_long_column, adx_column]
    if not all(col in data.columns for col in required_columns):
        return False
    
    current_short = data[sma_short_column].iloc[-1]
    current_long = data[sma_long_column].iloc[-1]
    prev_short = data[sma_short_column].iloc[-2]
    prev_long = data[sma_long_column].iloc[-2]
    current_adx = data[adx_column].iloc[-1]
    
    # 데드크로스 발생 + ADX 강세
    dead_cross = prev_short >= prev_long and current_short < current_long
    strong_trend = current_adx >= 25
    
    return dead_cross and strong_trend


def trend_continuation_bullish(data: pd.DataFrame) -> bool:
    """상승 추세 지속 확인 규칙"""
    sma_bullish = sma_bullish_alignment(data)
    macd_positive = macd_zero_line_bullish_cross(data) or analyze_macd_cross(data) in [
        MacdEvidence.BULLISH_MOMENTUM_INCREASE, MacdEvidence.BULLISH_MOMENTUM_CONTINUATION
    ]
    trend_strong = strong_uptrend_confirmed(data) or moderate_uptrend_confirmed(data)
    
    return sma_bullish and (macd_positive or trend_strong)


def trend_continuation_bearish(data: pd.DataFrame) -> bool:
    """하락 추세 지속 확인 규칙"""
    sma_bearish = sma_bearish_alignment(data)
    macd_negative = macd_zero_line_bearish_cross(data) or analyze_macd_cross(data) in [
        MacdEvidence.BEARISH_MOMENTUM_INCREASE, MacdEvidence.BEARISH_MOMENTUM_CONTINUATION
    ]
    trend_strong = strong_downtrend_confirmed(data) or moderate_downtrend_confirmed(data)
    
    return sma_bearish and (macd_negative or trend_strong)


def trend_reversal_bullish(data: pd.DataFrame) -> bool:
    """상승 추세 전환 확인 규칙"""
    macd_cross = macd_confirms_golden_cross(data)
    sma_cross = sma_bullish_cross(data)
    
    return macd_cross or sma_cross


def trend_reversal_bearish(data: pd.DataFrame) -> bool:
    """하락 추세 전환 확인 규칙"""
    macd_cross = macd_confirms_dead_cross(data)
    sma_cross = sma_bearish_cross(data)
    
    return macd_cross or sma_cross


# 추세 규칙 딕셔너리
TREND_RULES = {
    # MACD 크로스 규칙 (사용자 예시에 따른)
    'macd_confirms_golden_cross': macd_confirms_golden_cross,
    'macd_confirms_dead_cross': macd_confirms_dead_cross,
    'macd_zero_line_bullish_cross': macd_zero_line_bullish_cross,
    'macd_zero_line_bearish_cross': macd_zero_line_bearish_cross,
    
    # SMA 정배열 규칙
    'sma_bullish_alignment': sma_bullish_alignment,
    'sma_bearish_alignment': sma_bearish_alignment,
    'sma_bullish_cross': sma_bullish_cross,
    'sma_bearish_cross': sma_bearish_cross,
    
    # 추세 강도 규칙
    'strong_uptrend_confirmed': strong_uptrend_confirmed,
    'strong_downtrend_confirmed': strong_downtrend_confirmed,
    'moderate_uptrend_confirmed': moderate_uptrend_confirmed,
    'moderate_downtrend_confirmed': moderate_downtrend_confirmed,
    
    # 복합 추세 규칙
    'sma_golden_cross_with_trend': sma_golden_cross_with_trend,
    'sma_dead_cross_with_trend': sma_dead_cross_with_trend,
    'trend_continuation_bullish': trend_continuation_bullish,
    'trend_continuation_bearish': trend_continuation_bearish,
    'trend_reversal_bullish': trend_reversal_bullish,
    'trend_reversal_bearish': trend_reversal_bearish,
} 