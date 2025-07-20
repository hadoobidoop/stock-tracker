"""
Trend Analysis Module

SMA, MACD, ADX 등 추세 지표들의 복합 분석 로직을 제공합니다.
기존 CompositeDetector에서 분리된 추세 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Optional, Tuple

import pandas as pd

from domain.indicators.calculator import calculate_macd
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MacdEvidence(Enum):
    """MACD 근거 분류 (사용자 제공 예시 기반)"""
    GOLDEN_CROSS = "MACD 골든크로스"
    DEAD_CROSS = "MACD 데드크로스"
    BULLISH_DIVERGENCE = "MACD 강세 다이버전스"
    BEARISH_DIVERGENCE = "MACD 약세 다이버전스"
    ZERO_LINE_CROSS_UP = "MACD 0선 상향 돌파"
    ZERO_LINE_CROSS_DOWN = "MACD 0선 하향 돌파"
    STRENGTHENING_BULLISH = "MACD 상승 강화"
    STRENGTHENING_BEARISH = "MACD 하락 강화"


class SmaEvidence(Enum):
    """SMA 추세 근거 분류"""
    GOLDEN_CROSS = "SMA 골든크로스"
    DEAD_CROSS = "SMA 데드크로스"
    BULLISH_ALIGNMENT = "SMA 정배열"
    BEARISH_ALIGNMENT = "SMA 역배열"
    SUPPORT_BOUNCE = "SMA 지지선 반등"
    RESISTANCE_REJECTION = "SMA 저항선 거부"
    TREND_CONTINUATION = "SMA 추세 지속"


class TrendStrength(Enum):
    """추세 강도 분류"""
    VERY_STRONG = "매우 강한 추세"
    STRONG = "강한 추세"
    MODERATE = "보통 추세"
    WEAK = "약한 추세"
    SIDEWAYS = "횡보"


def analyze_macd_cross(data: pd.DataFrame, 
                      macd_column: str = 'MACD_12_26_9',
                      macd_signal_column: str = 'MACDs_12_26_9') -> MacdEvidence | None:
    """
    MACD 지표를 분석하여 크로스오버 근거를 반환합니다. (사용자 제공 예시 기반)
    
    Args:
        data: OHLCV 및 지표 데이터
        macd_column: MACD 컬럼명
        macd_signal_column: MACD Signal 컬럼명
        
    Returns:
        MacdEvidence | None: MACD 근거 또는 None
    """
    try:
        if len(data) < 2:
            return None
            
        prev = data.iloc[-2]
        last = data.iloc[-1]
        
        prev_macd = prev[macd_column]
        prev_signal = prev[macd_signal_column]
        curr_macd = last[macd_column]
        curr_signal = last[macd_signal_column]
        
        # 골든 크로스 (사용자 예시와 동일)
        if prev_macd < prev_signal and curr_macd > curr_signal:
            return MacdEvidence.GOLDEN_CROSS
        
        # 데드 크로스 (사용자 예시와 동일)
        if prev_macd > prev_signal and curr_macd < curr_signal:
            return MacdEvidence.DEAD_CROSS
        
        # 0선 돌파
        if prev_macd <= 0 < curr_macd:
            return MacdEvidence.ZERO_LINE_CROSS_UP
        elif prev_macd >= 0 > curr_macd:
            return MacdEvidence.ZERO_LINE_CROSS_DOWN
        
        # 추세 강화
        if curr_macd > curr_signal and curr_macd > prev_macd:
            return MacdEvidence.STRENGTHENING_BULLISH
        elif curr_macd < curr_signal and curr_macd < prev_macd:
            return MacdEvidence.STRENGTHENING_BEARISH
        
        return None
        
    except Exception as e:
        logger.error(f"MACD 크로스 분석 실패: {e}")
        return None


def analyze_sma_trend(data: pd.DataFrame,
                     short_sma_column: str = 'SMA_5',
                     long_sma_column: str = 'SMA_20',
                     price_column: str = 'Close') -> Tuple[SmaEvidence | None, float]:
    """
    SMA 추세를 분석하여 근거와 신호 강도를 반환합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        short_sma_column: 단기 SMA 컬럼명
        long_sma_column: 장기 SMA 컬럼명
        price_column: 가격 컬럼명
        
    Returns:
        Tuple[SmaEvidence | None, float]: (SMA 근거, 신호 강도)
    """
    try:
        if len(data) < 3:
            return None, 0.0
            
        prev = data.iloc[-2]
        curr = data.iloc[-1]
        prev2 = data.iloc[-3]
        
        prev_short = prev[short_sma_column]
        prev_long = prev[long_sma_column]
        curr_short = curr[short_sma_column]
        curr_long = curr[long_sma_column]
        curr_price = curr[price_column]
        
        # 골든/데드 크로스 감지
        if prev_short <= prev_long and curr_short > curr_long:
            strength = min((curr_short - curr_long) / curr_long * 100, 1.0)
            return SmaEvidence.GOLDEN_CROSS, 0.8 + strength
        elif prev_short >= prev_long and curr_short < curr_long:
            strength = min((curr_long - curr_short) / curr_long * 100, 1.0)
            return SmaEvidence.DEAD_CROSS, 0.8 + strength
        
        # 정배열/역배열 확인
        if curr_short > curr_long and curr_price > curr_short:
            return SmaEvidence.BULLISH_ALIGNMENT, 0.6
        elif curr_short < curr_long and curr_price < curr_short:
            return SmaEvidence.BEARISH_ALIGNMENT, 0.6
        
        # 지지/저항 확인
        if curr_price > curr_long and prev[price_column] <= prev_long:
            return SmaEvidence.SUPPORT_BOUNCE, 0.7
        elif curr_price < curr_long and prev[price_column] >= prev_long:
            return SmaEvidence.RESISTANCE_REJECTION, 0.7
        
        # 추세 지속
        if curr_short > curr_long and curr_short > prev_short:
            return SmaEvidence.TREND_CONTINUATION, 0.4
        elif curr_short < curr_long and curr_short < prev_short:
            return SmaEvidence.TREND_CONTINUATION, 0.4
        
        return None, 0.0
        
    except Exception as e:
        logger.error(f"SMA 추세 분석 실패: {e}")
        return None, 0.0


def analyze_trend_strength(data: pd.DataFrame,
                         adx_column: str = 'ADX_14',
                         dmp_column: str = 'DMP_14',
                         dmn_column: str = 'DMN_14') -> Tuple[TrendStrength, float]:
    """
    ADX를 기반으로 추세 강도를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        adx_column: ADX 컬럼명
        dmp_column: +DI 컬럼명
        dmn_column: -DI 컬럼명
        
    Returns:
        Tuple[TrendStrength, float]: (추세 강도, 방향성 점수)
    """
    try:
        if len(data) < 1:
            return TrendStrength.SIDEWAYS, 0.0
            
        latest = data.iloc[-1]
        adx = latest[adx_column]
        dmp = latest.get(dmp_column, 0)
        dmn = latest.get(dmn_column, 0)
        
        # 추세 강도 분류
        if adx >= 40:
            strength = TrendStrength.VERY_STRONG
        elif adx >= 25:
            strength = TrendStrength.STRONG
        elif adx >= 20:
            strength = TrendStrength.MODERATE
        elif adx >= 15:
            strength = TrendStrength.WEAK
        else:
            strength = TrendStrength.SIDEWAYS
        
        # 방향성 점수 계산 (+1: 상승, -1: 하락, 0: 중립)
        if dmp > dmn:
            direction_score = min((dmp - dmn) / max(dmp, dmn, 1), 1.0)
        elif dmn > dmp:
            direction_score = -min((dmn - dmp) / max(dmp, dmn, 1), 1.0)
        else:
            direction_score = 0.0
        
        return strength, direction_score
        
    except Exception as e:
        logger.error(f"추세 강도 분석 실패: {e}")
        return TrendStrength.SIDEWAYS, 0.0


def get_trend_consensus(data: pd.DataFrame,
                       short_sma_column: str = 'SMA_5',
                       long_sma_column: str = 'SMA_20',
                       macd_column: str = 'MACD_12_26_9',
                       macd_signal_column: str = 'MACDs_12_26_9',
                       adx_column: str = 'ADX_14') -> Dict[str, any]:
    """
    SMA, MACD, ADX를 종합하여 추세 컨센서스를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        
    Returns:
        Dict[str, any]: 종합 추세 분석 결과
    """
    try:
        # 각 지표별 분석
        macd_evidence = analyze_macd_cross(data, macd_column, macd_signal_column)
        sma_evidence, sma_strength = analyze_sma_trend(data, short_sma_column, long_sma_column)
        trend_strength, direction_score = analyze_trend_strength(data, adx_column)
        
        # 종합 점수 계산 (-3 ~ +3)
        total_score = 0
        evidences = []
        
        # MACD 점수
        if macd_evidence == MacdEvidence.GOLDEN_CROSS:
            total_score += 2
            evidences.append(macd_evidence.value)
        elif macd_evidence == MacdEvidence.DEAD_CROSS:
            total_score -= 2
            evidences.append(macd_evidence.value)
        elif macd_evidence in [MacdEvidence.ZERO_LINE_CROSS_UP, MacdEvidence.STRENGTHENING_BULLISH]:
            total_score += 1
            evidences.append(macd_evidence.value)
        elif macd_evidence in [MacdEvidence.ZERO_LINE_CROSS_DOWN, MacdEvidence.STRENGTHENING_BEARISH]:
            total_score -= 1
            evidences.append(macd_evidence.value)
        
        # SMA 점수
        if sma_evidence == SmaEvidence.GOLDEN_CROSS:
            total_score += 2
            evidences.append(sma_evidence.value)
        elif sma_evidence == SmaEvidence.DEAD_CROSS:
            total_score -= 2
            evidences.append(sma_evidence.value)
        elif sma_evidence in [SmaEvidence.BULLISH_ALIGNMENT, SmaEvidence.SUPPORT_BOUNCE]:
            total_score += 1
            evidences.append(sma_evidence.value)
        elif sma_evidence in [SmaEvidence.BEARISH_ALIGNMENT, SmaEvidence.RESISTANCE_REJECTION]:
            total_score -= 1
            evidences.append(sma_evidence.value)
        
        # ADX 방향성 점수
        if direction_score > 0.5:
            total_score += 1
        elif direction_score < -0.5:
            total_score -= 1
        
        # 최종 컨센서스 결정
        if total_score >= 3:
            consensus = "강한 상승 추세"
        elif total_score >= 1:
            consensus = "약한 상승 추세"
        elif total_score <= -3:
            consensus = "강한 하락 추세"
        elif total_score <= -1:
            consensus = "약한 하락 추세"
        else:
            consensus = "중립/횡보"
        
        return {
            "consensus": consensus,
            "total_score": total_score,
            "trend_strength": trend_strength.value,
            "direction_score": direction_score,
            "evidences": evidences,
            "macd_evidence": macd_evidence.value if macd_evidence else None,
            "sma_evidence": sma_evidence.value if sma_evidence else None,
            "sma_strength": sma_strength
        }
        
    except Exception as e:
        logger.error(f"추세 컨센서스 분석 실패: {e}")
        return {
            "consensus": "분석 실패",
            "total_score": 0,
            "trend_strength": TrendStrength.SIDEWAYS.value,
            "direction_score": 0.0,
            "evidences": [],
            "macd_evidence": None,
            "sma_evidence": None,
            "sma_strength": 0.0
        } 