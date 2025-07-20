"""
Trend Analysis Module

MACD 크로스, SMA 추세 등 추세 지표들의 복합 분석 로직을 제공합니다.
기존 CompositeDetector에서 분리된 추세 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Tuple

import pandas as pd

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MacdEvidence(Enum):
    """MACD 크로스 근거"""
    GOLDEN_CROSS = "MACD 골든크로스"
    DEAD_CROSS = "MACD 데드크로스"
    BULLISH_TREND = "MACD 상승 추세"
    BEARISH_TREND = "MACD 하락 추세"
    BULLISH_REVERSAL = "MACD 상승 반전"
    BEARISH_REVERSAL = "MACD 하락 반전"
    NEUTRAL = "MACD 중립"


class SmaTrendEvidence(Enum):
    """SMA 추세 근거"""
    GOLDEN_CROSS = "SMA 골든크로스"
    DEAD_CROSS = "SMA 데드크로스"
    BULLISH_ALIGNMENT = "SMA 상승 정배열"
    BEARISH_ALIGNMENT = "SMA 하락 정배열"
    TREND_CONTINUATION = "SMA 추세 지속"
    TREND_REVERSAL = "SMA 추세 반전"
    NEUTRAL = "SMA 중립"


class TrendStrength(Enum):
    """추세 강도 분류"""
    VERY_STRONG = "매우 강함"
    STRONG = "강함"
    MODERATE = "보통"
    WEAK = "약함"
    VERY_WEAK = "매우 약함"


def analyze_macd_cross(data: pd.DataFrame,
                       macd_column: str = 'MACD_12_26_9',
                       macd_signal_column: str = 'MACDs_12_26_9',
                       adx_column: str = 'ADX_14') -> Tuple[MacdEvidence, float]:
    """
    MACD 지표를 분석하여 크로스오버 근거를 반환합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        macd_column: MACD 컬럼명
        macd_signal_column: MACD Signal 컬럼명
        adx_column: ADX 컬럼명
        
    Returns:
        Tuple[MacdEvidence, float]: (근거, 신호 강도)
    """
    try:
        if len(data) < 2:
            return MacdEvidence.NEUTRAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # MACD 크로스 확인
        is_golden_cross = prev[macd_column] < prev[macd_signal_column] and latest[macd_column] > latest[macd_signal_column]
        is_dead_cross = prev[macd_column] > prev[macd_signal_column] and latest[macd_column] < latest[macd_signal_column]
        
        # ADX 강도 확인
        adx_strength = _get_adx_strength(latest[adx_column])
        
        # 크로스 이벤트 분석
        if is_golden_cross:
            strength = _calculate_macd_cross_strength(latest[macd_column], latest[macd_signal_column], adx_strength)
            return MacdEvidence.GOLDEN_CROSS, strength
        elif is_dead_cross:
            strength = _calculate_macd_cross_strength(latest[macd_column], latest[macd_signal_column], adx_strength)
            return MacdEvidence.DEAD_CROSS, strength
        
        # 추세 상태 분석
        if latest[macd_column] > latest[macd_signal_column]:
            if latest[macd_column] > prev[macd_column]:
                return MacdEvidence.BULLISH_TREND, 0.6
            else:
                return MacdEvidence.BULLISH_REVERSAL, 0.4
        elif latest[macd_column] < latest[macd_signal_column]:
            if latest[macd_column] < prev[macd_column]:
                return MacdEvidence.BEARISH_TREND, 0.6
            else:
                return MacdEvidence.BEARISH_REVERSAL, 0.4
        else:
            return MacdEvidence.NEUTRAL, 0.0
            
    except Exception as e:
        logger.error(f"MACD 크로스 분석 실패: {e}")
        return MacdEvidence.NEUTRAL, 0.0


def analyze_sma_trend(data: pd.DataFrame,
                     sma_short_column: str = 'SMA_5',
                     sma_long_column: str = 'SMA_20',
                     adx_column: str = 'ADX_14') -> Tuple[SmaTrendEvidence, float]:
    """
    SMA 이동평균을 분석하여 추세 근거를 반환합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        sma_short_column: 단기 SMA 컬럼명
        sma_long_column: 장기 SMA 컬럼명
        adx_column: ADX 컬럼명
        
    Returns:
        Tuple[SmaTrendEvidence, float]: (근거, 신호 강도)
    """
    try:
        if len(data) < 2:
            return SmaTrendEvidence.NEUTRAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # SMA 크로스 확인
        is_golden_cross = prev[sma_short_column] < prev[sma_long_column] and latest[sma_short_column] > latest[sma_long_column]
        is_dead_cross = prev[sma_short_column] > prev[sma_long_column] and latest[sma_short_column] < latest[sma_long_column]
        
        # ADX 강도 확인
        adx_strength = _get_adx_strength(latest[adx_column])
        
        # 크로스 이벤트 분석
        if is_golden_cross:
            strength = _calculate_sma_cross_strength(latest[sma_short_column], latest[sma_long_column], adx_strength)
            return SmaTrendEvidence.GOLDEN_CROSS, strength
        elif is_dead_cross:
            strength = _calculate_sma_cross_strength(latest[sma_short_column], latest[sma_long_column], adx_strength)
            return SmaTrendEvidence.DEAD_CROSS, strength
        
        # 정배열 상태 분석
        if latest[sma_short_column] > latest[sma_long_column]:
            if latest[sma_short_column] > prev[sma_short_column] and latest[sma_long_column] > prev[sma_long_column]:
                return SmaTrendEvidence.BULLISH_ALIGNMENT, 0.7
            else:
                return SmaTrendEvidence.TREND_CONTINUATION, 0.5
        elif latest[sma_short_column] < latest[sma_long_column]:
            if latest[sma_short_column] < prev[sma_short_column] and latest[sma_long_column] < prev[sma_long_column]:
                return SmaTrendEvidence.BEARISH_ALIGNMENT, 0.7
            else:
                return SmaTrendEvidence.TREND_CONTINUATION, 0.5
        else:
            return SmaTrendEvidence.NEUTRAL, 0.0
            
    except Exception as e:
        logger.error(f"SMA 추세 분석 실패: {e}")
        return SmaTrendEvidence.NEUTRAL, 0.0


def get_trend_strength(data: pd.DataFrame,
                      macd_column: str = 'MACD_12_26_9',
                      macd_signal_column: str = 'MACDs_12_26_9',
                      sma_short_column: str = 'SMA_5',
                      sma_long_column: str = 'SMA_20',
                      adx_column: str = 'ADX_14') -> TrendStrength:
    """
    여러 추세 지표를 종합하여 추세 강도를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        macd_column: MACD 컬럼명
        macd_signal_column: MACD Signal 컬럼명
        sma_short_column: 단기 SMA 컬럼명
        sma_long_column: 장기 SMA 컬럼명
        adx_column: ADX 컬럼명
        
    Returns:
        TrendStrength: 추세 강도
    """
    try:
        if len(data) < 2:
            return TrendStrength.NEUTRAL
            
        latest = data.iloc[-1]
        
        # 각 지표별 점수 계산
        macd_score = _calculate_macd_trend_score(latest[macd_column], latest[macd_signal_column])
        sma_score = _calculate_sma_trend_score(latest[sma_short_column], latest[sma_long_column])
        adx_score = _calculate_adx_trend_score(latest[adx_column])
        
        # 총 점수 계산
        total_score = macd_score + sma_score + adx_score
        
        # 강도 분류
        if total_score >= 8:
            return TrendStrength.VERY_STRONG
        elif total_score >= 5:
            return TrendStrength.STRONG
        elif total_score >= 2:
            return TrendStrength.MODERATE
        elif total_score >= -2:
            return TrendStrength.WEAK
        else:
            return TrendStrength.VERY_WEAK
            
    except Exception as e:
        logger.error(f"추세 강도 분석 실패: {e}")
        return TrendStrength.WEAK


def analyze_trend_alignment(data: pd.DataFrame,
                          lookback_periods: int = 5) -> Dict[str, float]:
    """
    단기/장기 추세의 일치도를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        lookback_periods: 분석 기간
        
    Returns:
        Dict[str, float]: 분석 결과
    """
    try:
        if len(data) < lookback_periods + 1:
            return {"alignment_score": 0.0, "trend_consistency": 0.0}
            
        recent_data = data.iloc[-lookback_periods:]
        
        # 단기/장기 추세 방향 계산
        short_trend = recent_data['SMA_5'].iloc[-1] - recent_data['SMA_5'].iloc[0]
        long_trend = recent_data['SMA_20'].iloc[-1] - recent_data['SMA_20'].iloc[0]
        
        # 일치도 점수 계산
        if (short_trend > 0 and long_trend > 0) or (short_trend < 0 and long_trend < 0):
            alignment_score = min(abs(short_trend) + abs(long_trend), 1.0)
        else:
            alignment_score = 0.0
        
        # 추세 일관성 계산
        trend_changes = 0
        for i in range(1, len(recent_data)):
            prev_short = recent_data['SMA_5'].iloc[i-1]
            curr_short = recent_data['SMA_5'].iloc[i]
            prev_long = recent_data['SMA_20'].iloc[i-1]
            curr_long = recent_data['SMA_20'].iloc[i]
            
            if (curr_short - prev_short) * (curr_long - prev_long) < 0:
                trend_changes += 1
        
        consistency_score = 1.0 - (trend_changes / (len(recent_data) - 1))
        
        return {
            "alignment_score": alignment_score,
            "trend_consistency": consistency_score
        }
        
    except Exception as e:
        logger.error(f"추세 일치도 분석 실패: {e}")
        return {"alignment_score": 0.0, "trend_consistency": 0.0}


def _get_adx_strength(adx_value: float) -> float:
    """ADX 강도를 반환합니다."""
    if adx_value >= 25:
        return 1.2  # 강한 추세
    elif adx_value >= 20:
        return 1.0  # 보통 추세
    else:
        return 0.8  # 약한 추세


def _calculate_macd_cross_strength(macd: float, macd_signal: float, adx_strength: float) -> float:
    """MACD 크로스 강도를 계산합니다."""
    base_strength = 0.8
    if abs(macd - macd_signal) > 0.1:  # 크로스 간격이 클 때
        base_strength += 0.2
    return base_strength * adx_strength


def _calculate_sma_cross_strength(sma_short: float, sma_long: float, adx_strength: float) -> float:
    """SMA 크로스 강도를 계산합니다."""
    base_strength = 0.8
    if abs(sma_short - sma_long) > 0.5:  # 크로스 간격이 클 때
        base_strength += 0.2
    return base_strength * adx_strength


def _calculate_macd_trend_score(macd: float, macd_signal: float) -> int:
    """MACD 추세 점수 계산 (-3 ~ +3)"""
    if macd > macd_signal:
        if macd > 0:
            return 3  # 0선 위에서 상승
        else:
            return 2  # 0선 아래에서 상승
    elif macd < macd_signal:
        if macd < 0:
            return -3  # 0선 아래에서 하락
        else:
            return -2  # 0선 위에서 하락
    else:
        return 0


def _calculate_sma_trend_score(sma_short: float, sma_long: float) -> int:
    """SMA 추세 점수 계산 (-3 ~ +3)"""
    if sma_short > sma_long:
        return 2  # 상승 정배열
    elif sma_short < sma_long:
        return -2  # 하락 정배열
    else:
        return 0


def _calculate_adx_trend_score(adx: float) -> int:
    """ADX 추세 점수 계산 (-3 ~ +3)"""
    if adx >= 25:
        return 3  # 강한 추세
    elif adx >= 20:
        return 1  # 보통 추세
    else:
        return 0  # 약한 추세 