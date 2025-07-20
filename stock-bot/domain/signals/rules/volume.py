"""
Volume Rules Module

거래량 지표 기반 거래 규칙들을 정의합니다.
analysis.volume 모듈의 함수들을 활용하여 재사용 가능한 규칙을 제공합니다.
"""

import pandas as pd
from typing import Callable

from ..analysis.volume import (
    analyze_macd_with_volume,
    get_volume_pattern,
    MacdVolumeEvidence,
    VolumePattern
)


def macd_bullish_with_volume_surge(data: pd.DataFrame) -> bool:
    """MACD 골든크로스와 거래량 급증 동시 확인"""
    evidence = analyze_macd_with_volume(data)
    return evidence == MacdVolumeEvidence.BULLISH_CROSS_WITH_VOLUME_SURGE


def macd_bearish_with_volume_surge(data: pd.DataFrame) -> bool:
    """MACD 데드크로스와 거래량 급증 동시 확인"""
    evidence = analyze_macd_with_volume(data)
    return evidence == MacdVolumeEvidence.BEARISH_CROSS_WITH_VOLUME_SURGE


def macd_bullish_trend_with_volume_confirm(data: pd.DataFrame) -> bool:
    """MACD 상승 추세와 거래량 확인"""
    evidence = analyze_macd_with_volume(data)
    return evidence == MacdVolumeEvidence.BULLISH_TREND_WITH_VOLUME_CONFIRM


def macd_bearish_trend_with_volume_confirm(data: pd.DataFrame) -> bool:
    """MACD 하락 추세와 거래량 확인"""
    evidence = analyze_macd_with_volume(data)
    return evidence == MacdVolumeEvidence.BEARISH_TREND_WITH_VOLUME_CONFIRM


def volume_surge_pattern(data: pd.DataFrame) -> bool:
    """거래량 급증 패턴 확인"""
    pattern = get_volume_pattern(data)
    return pattern == VolumePattern.SURGE


def volume_above_average_pattern(data: pd.DataFrame) -> bool:
    """거래량 평균 이상 패턴 확인"""
    pattern = get_volume_pattern(data)
    return pattern in [VolumePattern.SURGE, VolumePattern.ABOVE_AVERAGE]


def volume_declining_pattern(data: pd.DataFrame) -> bool:
    """거래량 감소 패턴 확인"""
    pattern = get_volume_pattern(data)
    return pattern == VolumePattern.DECLINING


def volume_breakout_confirmation(data: pd.DataFrame,
                               volume_column: str = 'Volume',
                               price_column: str = 'Close',
                               volume_multiplier: float = 1.5) -> bool:
    """가격 돌파와 거래량 증가 동시 확인"""
    if len(data) < 21:  # 20일 평균 + 현재
        return False
    
    if volume_column not in data.columns or price_column not in data.columns:
        return False
    
    current_volume = data[volume_column].iloc[-1]
    avg_volume = data[volume_column].rolling(20).mean().iloc[-1]
    current_price = data[price_column].iloc[-1]
    prev_price = data[price_column].iloc[-2]
    
    # 거래량이 평균의 1.5배 이상이고 가격이 상승
    volume_surge = current_volume > avg_volume * volume_multiplier
    price_increase = current_price > prev_price
    
    return volume_surge and price_increase


def volume_breakdown_confirmation(data: pd.DataFrame,
                                volume_column: str = 'Volume',
                                price_column: str = 'Close',
                                volume_multiplier: float = 1.5) -> bool:
    """가격 하락과 거래량 증가 동시 확인"""
    if len(data) < 21:  # 20일 평균 + 현재
        return False
    
    if volume_column not in data.columns or price_column not in data.columns:
        return False
    
    current_volume = data[volume_column].iloc[-1]
    avg_volume = data[volume_column].rolling(20).mean().iloc[-1]
    current_price = data[price_column].iloc[-1]
    prev_price = data[price_column].iloc[-2]
    
    # 거래량이 평균의 1.5배 이상이고 가격이 하락
    volume_surge = current_volume > avg_volume * volume_multiplier
    price_decrease = current_price < prev_price
    
    return volume_surge and price_decrease


def volume_exhaustion_bullish(data: pd.DataFrame,
                            volume_column: str = 'Volume',
                            price_column: str = 'Close') -> bool:
    """하락 중 거래량 고갈 후 반등 신호"""
    if len(data) < 5:
        return False
    
    if volume_column not in data.columns or price_column not in data.columns:
        return False
    
    # 최근 3일 거래량 감소 추세
    recent_volumes = data[volume_column].iloc[-3:].tolist()
    volume_declining = all(recent_volumes[i] > recent_volumes[i+1] for i in range(len(recent_volumes)-1))
    
    # 가격은 하락했다가 반등
    prices = data[price_column].iloc[-3:].tolist()
    price_recovery = prices[-1] > prices[-2] and prices[-2] < prices[-3]
    
    return volume_declining and price_recovery


def volume_exhaustion_bearish(data: pd.DataFrame,
                            volume_column: str = 'Volume',
                            price_column: str = 'Close') -> bool:
    """상승 중 거래량 고갈 후 하락 신호"""
    if len(data) < 5:
        return False
    
    if volume_column not in data.columns or price_column not in data.columns:
        return False
    
    # 최근 3일 거래량 감소 추세
    recent_volumes = data[volume_column].iloc[-3:].tolist()
    volume_declining = all(recent_volumes[i] > recent_volumes[i+1] for i in range(len(recent_volumes)-1))
    
    # 가격은 상승했다가 하락
    prices = data[price_column].iloc[-3:].tolist()
    price_breakdown = prices[-1] < prices[-2] and prices[-2] > prices[-3]
    
    return volume_declining and price_breakdown


def volume_accumulation_pattern(data: pd.DataFrame,
                              volume_column: str = 'Volume',
                              lookback_period: int = 10) -> bool:
    """거래량 누적(매집) 패턴 확인"""
    if len(data) < lookback_period + 5:
        return False
    
    if volume_column not in data.columns:
        return False
    
    # 최근 기간 평균 거래량이 이전 기간보다 증가
    recent_avg = data[volume_column].iloc[-lookback_period:].mean()
    prev_avg = data[volume_column].iloc[-lookback_period*2:-lookback_period].mean()
    
    return recent_avg > prev_avg * 1.2


def volume_distribution_pattern(data: pd.DataFrame,
                              volume_column: str = 'Volume',
                              lookback_period: int = 10) -> bool:
    """거래량 분산(매도) 패턴 확인"""
    if len(data) < lookback_period + 5:
        return False
    
    if volume_column not in data.columns:
        return False
    
    # 최근 기간 평균 거래량이 이전 기간보다 감소
    recent_avg = data[volume_column].iloc[-lookback_period:].mean()
    prev_avg = data[volume_column].iloc[-lookback_period*2:-lookback_period].mean()
    
    return recent_avg < prev_avg * 0.8


# 거래량 규칙 딕셔너리
VOLUME_RULES = {
    # MACD + 거래량 조합 규칙
    'macd_bullish_with_volume_surge': macd_bullish_with_volume_surge,
    'macd_bearish_with_volume_surge': macd_bearish_with_volume_surge,
    'macd_bullish_trend_with_volume_confirm': macd_bullish_trend_with_volume_confirm,
    'macd_bearish_trend_with_volume_confirm': macd_bearish_trend_with_volume_confirm,
    
    # 거래량 패턴 규칙
    'volume_surge_pattern': volume_surge_pattern,
    'volume_above_average_pattern': volume_above_average_pattern,
    'volume_declining_pattern': volume_declining_pattern,
    
    # 가격 + 거래량 확인 규칙
    'volume_breakout_confirmation': volume_breakout_confirmation,
    'volume_breakdown_confirmation': volume_breakdown_confirmation,
    'volume_exhaustion_bullish': volume_exhaustion_bullish,
    'volume_exhaustion_bearish': volume_exhaustion_bearish,
    
    # 매집/매도 패턴 규칙
    'volume_accumulation_pattern': volume_accumulation_pattern,
    'volume_distribution_pattern': volume_distribution_pattern,
} 