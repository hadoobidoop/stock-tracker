"""
Volatility Rules Module

변동성 지표(BB, ADX) 기반 거래 규칙들을 정의합니다.
analysis.volatility 모듈의 함수들을 활용하여 재사용 가능한 규칙을 제공합니다.
"""

import pandas as pd
from typing import Callable

from ..analysis.volatility import (
    analyze_bb_volatility_with_trend,
    get_volatility_regime,
    get_bb_band_position,
    analyze_squeeze_breakout_potential,
    BBVolatilityEvidence,
    VolatilityRegime,
    BBBandPosition
)


def bb_squeeze_with_strong_trend(data: pd.DataFrame) -> bool:
    """밴드 스퀴즈 중 강한 추세 형성 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.SQUEEZE_WITH_STRONG_TREND


def bb_breakout_with_strong_trend(data: pd.DataFrame) -> bool:
    """상단 돌파 및 강한 상승 추세 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.BREAKOUT_WITH_STRONG_TREND


def bb_breakdown_with_strong_trend(data: pd.DataFrame) -> bool:
    """하단 돌파 및 강한 하락 추세 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.BREAKDOWN_WITH_STRONG_TREND


def bb_expansion_with_moderate_trend(data: pd.DataFrame) -> bool:
    """밴드 확장 및 보통 추세 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.EXPANSION_WITH_MODERATE_TREND


def bb_mean_reversion_strong_signal(data: pd.DataFrame) -> bool:
    """강한 평균 회귀 신호 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.MEAN_REVERSION_STRONG


def bb_mean_reversion_weak_signal(data: pd.DataFrame) -> bool:
    """약한 평균 회귀 신호 확인"""
    evidence = analyze_bb_volatility_with_trend(data)
    return evidence == BBVolatilityEvidence.MEAN_REVERSION_WEAK


def high_volatility_trending_regime(data: pd.DataFrame) -> bool:
    """고변동성 추세 체제 확인"""
    regime = get_volatility_regime(data)
    return regime == VolatilityRegime.HIGH_VOLATILITY_TRENDING


def high_volatility_sideways_regime(data: pd.DataFrame) -> bool:
    """고변동성 횡보 체제 확인"""
    regime = get_volatility_regime(data)
    return regime == VolatilityRegime.HIGH_VOLATILITY_SIDEWAYS


def low_volatility_squeeze_regime(data: pd.DataFrame) -> bool:
    """저변동성 압축 체제 확인"""
    regime = get_volatility_regime(data)
    return regime == VolatilityRegime.LOW_VOLATILITY_SQUEEZE


def expanding_volatility_regime(data: pd.DataFrame) -> bool:
    """변동성 확장 체제 확인"""
    regime = get_volatility_regime(data)
    return regime == VolatilityRegime.EXPANDING_VOLATILITY


def bb_price_above_upper_band(data: pd.DataFrame) -> bool:
    """가격이 상단 밴드 위에 위치"""
    position = get_bb_band_position(data)
    return position == BBBandPosition.ABOVE_UPPER


def bb_price_below_lower_band(data: pd.DataFrame) -> bool:
    """가격이 하단 밴드 아래에 위치"""
    position = get_bb_band_position(data)
    return position == BBBandPosition.BELOW_LOWER


def bb_price_near_upper_band(data: pd.DataFrame) -> bool:
    """가격이 상단 밴드 근처에 위치"""
    position = get_bb_band_position(data)
    return position in [BBBandPosition.ABOVE_UPPER, BBBandPosition.NEAR_UPPER]


def bb_price_near_lower_band(data: pd.DataFrame) -> bool:
    """가격이 하단 밴드 근처에 위치"""
    position = get_bb_band_position(data)
    return position in [BBBandPosition.BELOW_LOWER, BBBandPosition.NEAR_LOWER]


def bb_price_middle_zone(data: pd.DataFrame) -> bool:
    """가격이 중간 영역에 위치"""
    position = get_bb_band_position(data)
    return position in [BBBandPosition.MIDDLE_UPPER, BBBandPosition.MIDDLE_LOWER]


def squeeze_breakout_high_potential(data: pd.DataFrame) -> bool:
    """스퀴즈 돌파 높은 가능성 확인"""
    analysis = analyze_squeeze_breakout_potential(data)
    return analysis.get("potential") == "high"


def squeeze_breakout_moderate_potential(data: pd.DataFrame) -> bool:
    """스퀴즈 돌파 보통 가능성 확인"""
    analysis = analyze_squeeze_breakout_potential(data)
    return analysis.get("potential") in ["high", "moderate"]


def volatility_breakout_bullish(data: pd.DataFrame,
                              bb_upper_column: str = 'BBU_20_2.0',
                              volume_column: str = 'Volume',
                              price_column: str = 'Close') -> bool:
    """변동성 돌파 매수 신호 (상단 돌파 + 거래량)"""
    if len(data) < 2:
        return False
    
    required_columns = [bb_upper_column, volume_column, price_column]
    if not all(col in data.columns for col in required_columns):
        return False
    
    current_price = data[price_column].iloc[-1]
    prev_price = data[price_column].iloc[-2]
    current_bb_upper = data[bb_upper_column].iloc[-1]
    prev_bb_upper = data[bb_upper_column].iloc[-2]
    
    # 상단 밴드 돌파
    upper_breakout = (prev_price <= prev_bb_upper and 
                     current_price > current_bb_upper)
    
    # 거래량 증가 확인
    volume_surge = analyze_squeeze_breakout_potential(data).get("volume_ratio", 1.0) > 1.1
    
    return upper_breakout and volume_surge


def volatility_breakout_bearish(data: pd.DataFrame,
                              bb_lower_column: str = 'BBL_20_2.0',
                              volume_column: str = 'Volume',
                              price_column: str = 'Close') -> bool:
    """변동성 돌파 매도 신호 (하단 돌파 + 거래량)"""
    if len(data) < 2:
        return False
    
    required_columns = [bb_lower_column, volume_column, price_column]
    if not all(col in data.columns for col in required_columns):
        return False
    
    current_price = data[price_column].iloc[-1]
    prev_price = data[price_column].iloc[-2]
    current_bb_lower = data[bb_lower_column].iloc[-1]
    prev_bb_lower = data[bb_lower_column].iloc[-2]
    
    # 하단 밴드 돌파
    lower_breakout = (prev_price >= prev_bb_lower and 
                     current_price < current_bb_lower)
    
    # 거래량 증가 확인
    volume_surge = analyze_squeeze_breakout_potential(data).get("volume_ratio", 1.0) > 1.1
    
    return lower_breakout and volume_surge


def volatility_mean_reversion_bullish(data: pd.DataFrame) -> bool:
    """변동성 평균 회귀 매수 신호"""
    # 하단 밴드 근처에서 평균 회귀 신호
    near_lower = bb_price_near_lower_band(data)
    mean_reversion = bb_mean_reversion_strong_signal(data) or bb_mean_reversion_weak_signal(data)
    
    return near_lower and mean_reversion


def volatility_mean_reversion_bearish(data: pd.DataFrame) -> bool:
    """변동성 평균 회귀 매도 신호"""
    # 상단 밴드 근처에서 평균 회귀 신호
    near_upper = bb_price_near_upper_band(data)
    mean_reversion = bb_mean_reversion_strong_signal(data) or bb_mean_reversion_weak_signal(data)
    
    return near_upper and mean_reversion


# 변동성 규칙 딕셔너리
VOLATILITY_RULES = {
    # BB + ADX 조합 규칙
    'bb_squeeze_with_strong_trend': bb_squeeze_with_strong_trend,
    'bb_breakout_with_strong_trend': bb_breakout_with_strong_trend,
    'bb_breakdown_with_strong_trend': bb_breakdown_with_strong_trend,
    'bb_expansion_with_moderate_trend': bb_expansion_with_moderate_trend,
    'bb_mean_reversion_strong_signal': bb_mean_reversion_strong_signal,
    'bb_mean_reversion_weak_signal': bb_mean_reversion_weak_signal,
    
    # 변동성 체제 규칙
    'high_volatility_trending_regime': high_volatility_trending_regime,
    'high_volatility_sideways_regime': high_volatility_sideways_regime,
    'low_volatility_squeeze_regime': low_volatility_squeeze_regime,
    'expanding_volatility_regime': expanding_volatility_regime,
    
    # BB 밴드 위치 규칙
    'bb_price_above_upper_band': bb_price_above_upper_band,
    'bb_price_below_lower_band': bb_price_below_lower_band,
    'bb_price_near_upper_band': bb_price_near_upper_band,
    'bb_price_near_lower_band': bb_price_near_lower_band,
    'bb_price_middle_zone': bb_price_middle_zone,
    
    # 스퀴즈 돌파 규칙
    'squeeze_breakout_high_potential': squeeze_breakout_high_potential,
    'squeeze_breakout_moderate_potential': squeeze_breakout_moderate_potential,
    
    # 변동성 거래 규칙
    'volatility_breakout_bullish': volatility_breakout_bullish,
    'volatility_breakout_bearish': volatility_breakout_bearish,
    'volatility_mean_reversion_bullish': volatility_mean_reversion_bullish,
    'volatility_mean_reversion_bearish': volatility_mean_reversion_bearish,
} 