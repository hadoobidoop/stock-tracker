"""
Volatility Analysis Module

BB(볼린저밴드), ADX 등 변동성 지표들의 복합 분석 로직을 제공합니다.
기존 BBDetector와 관련 로직에서 분리된 변동성 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Optional, Tuple

import pandas as pd
import numpy as np

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BBVolatilityEvidence(Enum):
    """볼린저밴드 + ADX 변동성 조합 근거"""
    SQUEEZE_WITH_STRONG_TREND = "밴드 스퀴즈 중 강한 추세 형성"
    BREAKOUT_WITH_STRONG_TREND = "상단 돌파 및 강한 상승 추세"
    BREAKDOWN_WITH_STRONG_TREND = "하단 돌파 및 강한 하락 추세"
    SQUEEZE_WITH_WEAK_TREND = "밴드 스퀴즈 중 약한 추세"
    EXPANSION_WITH_MODERATE_TREND = "밴드 확장 및 보통 추세"
    MEAN_REVERSION_STRONG = "강한 평균 회귀 신호"
    MEAN_REVERSION_WEAK = "약한 평균 회귀 신호"
    NEUTRAL = "중립"
    NO_SIGNAL = "신호 없음"


class VolatilityRegime(Enum):
    """변동성 체제 분류"""
    HIGH_VOLATILITY_TRENDING = "고변동성 추세"
    HIGH_VOLATILITY_SIDEWAYS = "고변동성 횡보"
    MODERATE_VOLATILITY = "보통 변동성"
    LOW_VOLATILITY_SQUEEZE = "저변동성 압축"
    EXPANDING_VOLATILITY = "변동성 확장"


class BBBandPosition(Enum):
    """볼린저밴드 내 위치"""
    ABOVE_UPPER = "상단 밴드 위"
    NEAR_UPPER = "상단 밴드 근처"
    MIDDLE_UPPER = "중간선 위"
    MIDDLE_LOWER = "중간선 아래"
    NEAR_LOWER = "하단 밴드 근처"
    BELOW_LOWER = "하단 밴드 아래"


def analyze_bb_volatility_with_trend(data: pd.DataFrame,
                                   bb_upper_column: str = 'BBU_20_2.0',
                                   bb_middle_column: str = 'BBM_20_2.0',
                                   bb_lower_column: str = 'BBL_20_2.0',
                                   bb_bandwidth_column: str = 'BBB_20_2.0',
                                   bb_percent_column: str = 'BBP_20_2.0',
                                   adx_column: str = 'ADX_14',
                                   adx_strong_threshold: float = 25.0,
                                   adx_weak_threshold: float = 20.0,
                                   price_column: str = 'Close') -> BBVolatilityEvidence:
    """
    볼린저밴드와 ADX를 종합하여 변동성 기반 신호를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_upper_column: 볼린저밴드 상단 컬럼명
        bb_middle_column: 볼린저밴드 중간선 컬럼명  
        bb_lower_column: 볼린저밴드 하단 컬럼명
        bb_bandwidth_column: 볼린저밴드 대역폭 컬럼명
        bb_percent_column: 볼린저밴드 %B 컬럼명
        adx_column: ADX 컬럼명
        adx_strong_threshold: ADX 강한 추세 임계값
        adx_weak_threshold: ADX 약한 추세 임계값
        price_column: 가격 컬럼명
        
    Returns:
        BBVolatilityEvidence: 변동성 분석 결과
    """
    try:
        if len(data) < 2:
            return BBVolatilityEvidence.NO_SIGNAL
            
        # 필요한 컬럼 확인
        required_columns = [bb_upper_column, bb_middle_column, bb_lower_column, 
                          bb_bandwidth_column, bb_percent_column, adx_column, price_column]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.warning(f"Missing columns for BB volatility analysis: {missing_columns}")
            return BBVolatilityEvidence.NO_SIGNAL
            
        current_data = data.iloc[-1]
        prev_data = data.iloc[-2]
        
        # 현재 지표값들
        current_price = current_data[price_column]
        current_bb_upper = current_data[bb_upper_column]
        current_bb_middle = current_data[bb_middle_column]
        current_bb_lower = current_data[bb_lower_column]
        current_bandwidth = current_data[bb_bandwidth_column]
        current_bb_percent = current_data[bb_percent_column]
        current_adx = current_data[adx_column]
        
        # 이전 지표값들
        prev_bandwidth = prev_data[bb_bandwidth_column]
        prev_bb_percent = prev_data[bb_percent_column]
        
        # 밴드 스퀴즈 여부 (bandwidth가 낮은 수준)
        bandwidth_ma = data[bb_bandwidth_column].rolling(20).mean().iloc[-1]
        is_squeeze = current_bandwidth < bandwidth_ma * 0.8
        
        # 밴드 확장 여부
        is_expanding = current_bandwidth > prev_bandwidth * 1.1
        
        # 돌파 확인
        upper_breakout = current_price > current_bb_upper and prev_data[price_column] <= prev_data[bb_upper_column]
        lower_breakout = current_price < current_bb_lower and prev_data[price_column] >= prev_data[bb_lower_column]
        
        # ADX 기반 추세 강도 분류
        if current_adx >= adx_strong_threshold:
            trend_strength = "STRONG"
        elif current_adx >= adx_weak_threshold:
            trend_strength = "MODERATE"
        else:
            trend_strength = "WEAK"
            
        # 조합 분석
        if is_squeeze and trend_strength == "STRONG":
            return BBVolatilityEvidence.SQUEEZE_WITH_STRONG_TREND
        elif is_squeeze and trend_strength == "WEAK":
            return BBVolatilityEvidence.SQUEEZE_WITH_WEAK_TREND
        elif upper_breakout and trend_strength == "STRONG":
            return BBVolatilityEvidence.BREAKOUT_WITH_STRONG_TREND
        elif lower_breakout and trend_strength == "STRONG":
            return BBVolatilityEvidence.BREAKDOWN_WITH_STRONG_TREND
        elif is_expanding and trend_strength == "MODERATE":
            return BBVolatilityEvidence.EXPANSION_WITH_MODERATE_TREND
        elif current_bb_percent <= 0.2 and trend_strength in ["MODERATE", "STRONG"]:
            return BBVolatilityEvidence.MEAN_REVERSION_STRONG
        elif current_bb_percent >= 0.8 and trend_strength in ["MODERATE", "STRONG"]:
            return BBVolatilityEvidence.MEAN_REVERSION_STRONG
        elif current_bb_percent <= 0.3 or current_bb_percent >= 0.7:
            return BBVolatilityEvidence.MEAN_REVERSION_WEAK
        else:
            return BBVolatilityEvidence.NEUTRAL
            
    except Exception as e:
        logger.error(f"Error in BB volatility analysis: {e}")
        return BBVolatilityEvidence.NO_SIGNAL


def get_volatility_regime(data: pd.DataFrame,
                         bb_bandwidth_column: str = 'BBB_20_2.0',
                         adx_column: str = 'ADX_14',
                         atr_column: str = 'ATR_14',
                         lookback_period: int = 20) -> VolatilityRegime:
    """
    변동성 체제를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_bandwidth_column: 볼린저밴드 대역폭 컬럼명
        adx_column: ADX 컬럼명
        atr_column: ATR 컬럼명 (없으면 생략)
        lookback_period: 변동성 비교 기간
        
    Returns:
        VolatilityRegime: 변동성 체제 분류
    """
    try:
        if len(data) < lookback_period:
            return VolatilityRegime.MODERATE_VOLATILITY
            
        # 필요한 컬럼 확인
        required_columns = [bb_bandwidth_column, adx_column]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.warning(f"Missing columns for volatility regime analysis: {missing_columns}")
            return VolatilityRegime.MODERATE_VOLATILITY
            
        current_data = data.iloc[-1]
        current_bandwidth = current_data[bb_bandwidth_column]
        current_adx = current_data[adx_column]
        
        # 최근 기간 평균과 비교
        bandwidth_ma = data[bb_bandwidth_column].rolling(lookback_period).mean().iloc[-1]
        bandwidth_std = data[bb_bandwidth_column].rolling(lookback_period).std().iloc[-1]
        
        # 변동성 수준 분류
        high_volatility_threshold = bandwidth_ma + bandwidth_std
        low_volatility_threshold = bandwidth_ma - bandwidth_std * 0.5
        
        # 변동성 확장 여부
        recent_bandwidth_trend = data[bb_bandwidth_column].rolling(5).mean().iloc[-1]
        prev_bandwidth_trend = data[bb_bandwidth_column].rolling(5).mean().iloc[-6]
        is_expanding = recent_bandwidth_trend > prev_bandwidth_trend * 1.1
        
        # 조합 분석
        if current_bandwidth > high_volatility_threshold:
            if current_adx >= 25:
                return VolatilityRegime.HIGH_VOLATILITY_TRENDING
            else:
                return VolatilityRegime.HIGH_VOLATILITY_SIDEWAYS
        elif current_bandwidth < low_volatility_threshold:
            return VolatilityRegime.LOW_VOLATILITY_SQUEEZE
        elif is_expanding:
            return VolatilityRegime.EXPANDING_VOLATILITY
        else:
            return VolatilityRegime.MODERATE_VOLATILITY
            
    except Exception as e:
        logger.error(f"Error in volatility regime analysis: {e}")
        return VolatilityRegime.MODERATE_VOLATILITY


def get_bb_band_position(data: pd.DataFrame,
                        bb_upper_column: str = 'BBU_20_2.0',
                        bb_middle_column: str = 'BBM_20_2.0',
                        bb_lower_column: str = 'BBL_20_2.0',
                        bb_percent_column: str = 'BBP_20_2.0',
                        price_column: str = 'Close',
                        near_threshold: float = 0.1) -> BBBandPosition:
    """
    현재 가격의 볼린저밴드 내 위치를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_upper_column: 볼린저밴드 상단 컬럼명
        bb_middle_column: 볼린저밴드 중간선 컬럼명
        bb_lower_column: 볼린저밴드 하단 컬럼명
        bb_percent_column: 볼린저밴드 %B 컬럼명
        price_column: 가격 컬럼명
        near_threshold: '근처' 판단 임계값
        
    Returns:
        BBBandPosition: 밴드 내 위치
    """
    try:
        if len(data) < 1:
            return BBBandPosition.MIDDLE_LOWER
            
        # 필요한 컬럼 확인
        required_columns = [bb_upper_column, bb_middle_column, bb_lower_column, 
                          bb_percent_column, price_column]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.warning(f"Missing columns for BB position analysis: {missing_columns}")
            return BBBandPosition.MIDDLE_LOWER
            
        current_data = data.iloc[-1]
        current_price = current_data[price_column]
        current_bb_upper = current_data[bb_upper_column]
        current_bb_middle = current_data[bb_middle_column]
        current_bb_lower = current_data[bb_lower_column]
        current_bb_percent = current_data[bb_percent_column]
        
        # %B 기반 위치 분석
        if current_bb_percent > 1.0:
            return BBBandPosition.ABOVE_UPPER
        elif current_bb_percent > (1.0 - near_threshold):
            return BBBandPosition.NEAR_UPPER
        elif current_bb_percent > 0.5:
            return BBBandPosition.MIDDLE_UPPER
        elif current_bb_percent > near_threshold:
            return BBBandPosition.MIDDLE_LOWER
        elif current_bb_percent > 0.0:
            return BBBandPosition.NEAR_LOWER
        else:
            return BBBandPosition.BELOW_LOWER
            
    except Exception as e:
        logger.error(f"Error in BB position analysis: {e}")
        return BBBandPosition.MIDDLE_LOWER


def analyze_squeeze_breakout_potential(data: pd.DataFrame,
                                     bb_bandwidth_column: str = 'BBB_20_2.0',
                                     adx_column: str = 'ADX_14',
                                     volume_column: str = 'Volume',
                                     lookback_period: int = 20) -> Dict[str, any]:
    """
    스퀴즈 상태에서 돌파 가능성을 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_bandwidth_column: 볼린저밴드 대역폭 컬럼명
        adx_column: ADX 컬럼명
        volume_column: 거래량 컬럼명
        lookback_period: 분석 기간
        
    Returns:
        Dict: 돌파 가능성 분석 결과
    """
    try:
        if len(data) < lookback_period:
            return {"potential": "unknown", "confidence": 0.0, "factors": []}
            
        # 필요한 컬럼 확인
        required_columns = [bb_bandwidth_column, adx_column, volume_column]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.warning(f"Missing columns for squeeze analysis: {missing_columns}")
            return {"potential": "unknown", "confidence": 0.0, "factors": []}
            
        current_data = data.iloc[-1]
        current_bandwidth = current_data[bb_bandwidth_column]
        current_adx = current_data[adx_column]
        current_volume = current_data[volume_column]
        
        # 스퀴즈 강도 분석
        bandwidth_ma = data[bb_bandwidth_column].rolling(lookback_period).mean().iloc[-1]
        bandwidth_percentile = data[bb_bandwidth_column].rolling(50).rank(pct=True).iloc[-1]
        
        # 거래량 패턴 분석
        volume_ma = data[volume_column].rolling(lookback_period).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
        
        # 분석 요소들
        factors = []
        confidence = 0.0
        
        # 스퀴즈 강도 (낮을수록 강한 스퀴즈)
        if bandwidth_percentile < 0.2:
            factors.append("매우 강한 스퀴즈")
            confidence += 0.3
        elif bandwidth_percentile < 0.4:
            factors.append("강한 스퀴즈")
            confidence += 0.2
        
        # ADX 상승 추세
        adx_trend = data[adx_column].rolling(5).mean().iloc[-1] - data[adx_column].rolling(5).mean().iloc[-6]
        if adx_trend > 0:
            factors.append("ADX 상승 중")
            confidence += 0.15
            
        # 거래량 증가
        if volume_ratio > 1.2:
            factors.append("거래량 증가")
            confidence += 0.2
        elif volume_ratio > 1.0:
            factors.append("거래량 보통")
            confidence += 0.1
            
        # 잠재력 분류
        if confidence >= 0.5:
            potential = "high"
        elif confidence >= 0.3:
            potential = "moderate"
        elif confidence >= 0.1:
            potential = "low"
        else:
            potential = "minimal"
            
        return {
            "potential": potential,
            "confidence": confidence,
            "factors": factors,
            "squeeze_strength": 1.0 - bandwidth_percentile,
            "volume_ratio": volume_ratio,
            "adx_trend": adx_trend
        }
        
    except Exception as e:
        logger.error(f"Error in squeeze breakout analysis: {e}")
        return {"potential": "unknown", "confidence": 0.0, "factors": []} 