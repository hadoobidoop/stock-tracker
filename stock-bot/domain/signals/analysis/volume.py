"""
Volume Analysis Module

MACD와 거래량 조합 분석 로직을 제공합니다.
기존 MACDVolumeDetector에서 분리된 거래량 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Tuple

import pandas as pd

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MacdVolumeEvidence(Enum):
    """MACD + 거래량 조합 근거"""
    BULLISH_CROSS_WITH_VOLUME_SURGE = "MACD 골든크로스 및 상승 거래량 급증"
    BULLISH_TREND_WITH_VOLUME_CONFIRM = "MACD 상승 추세 및 거래량 확인"
    BEARISH_CROSS_WITH_VOLUME_SURGE = "MACD 데드크로스 및 하락 거래량 급증"
    BEARISH_TREND_WITH_VOLUME_CONFIRM = "MACD 하락 추세 및 거래량 확인"
    WEAK_SIGNAL = "약한 신호"
    NO_SIGNAL = "신호 없음"


class VolumePattern(Enum):
    """거래량 패턴 분류"""
    SURGE = "급증"
    ABOVE_AVERAGE = "평균 이상"
    BELOW_AVERAGE = "평균 이하"
    DECLINING = "감소"
    NEUTRAL = "중립"


def analyze_macd_with_volume(data: pd.DataFrame,
                           macd_column: str = 'MACD_12_26_9',
                           macd_signal_column: str = 'MACDs_12_26_9',
                           volume_column: str = 'Volume',
                           volume_sma_column: str = 'Volume_SMA_20',
                           volume_surge_factor: float = 1.5) -> Tuple[MacdVolumeEvidence, float]:
    """
    MACD와 거래량을 조합하여 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        macd_column: MACD 컬럼명
        macd_signal_column: MACD Signal 컬럼명
        volume_column: 거래량 컬럼명
        volume_sma_column: 거래량 이동평균 컬럼명
        volume_surge_factor: 거래량 급증 임계값
        
    Returns:
        Tuple[MacdVolumeEvidence, float]: (근거, 신호 강도)
    """
    try:
        if len(data) < 2:
            return MacdVolumeEvidence.NO_SIGNAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # MACD 상태 및 이벤트 정의
        is_golden_cross = prev[macd_column] < prev[macd_signal_column] and latest[macd_column] > latest[macd_signal_column]
        is_dead_cross = prev[macd_column] > prev[macd_signal_column] and latest[macd_column] < latest[macd_signal_column]
        is_bullish_state = latest[macd_column] > latest[macd_signal_column]
        is_bearish_state = latest[macd_column] < latest[macd_signal_column]
        
        # 거래량 상태 확인
        volume_pattern = get_volume_pattern(data, volume_column, volume_sma_column, volume_surge_factor)
        
        # 가격 변화 확인
        is_price_rising = latest['Close'] > prev['Close']
        is_price_falling = latest['Close'] < prev['Close']
        
        # 조합 분석
        if is_golden_cross and volume_pattern == VolumePattern.SURGE and is_price_rising:
            return MacdVolumeEvidence.BULLISH_CROSS_WITH_VOLUME_SURGE, 1.0
        elif is_bullish_state and volume_pattern in [VolumePattern.SURGE, VolumePattern.ABOVE_AVERAGE] and is_price_rising:
            return MacdVolumeEvidence.BULLISH_TREND_WITH_VOLUME_CONFIRM, 0.7
        elif is_dead_cross and volume_pattern == VolumePattern.SURGE and is_price_falling:
            return MacdVolumeEvidence.BEARISH_CROSS_WITH_VOLUME_SURGE, 1.0
        elif is_bearish_state and volume_pattern in [VolumePattern.SURGE, VolumePattern.ABOVE_AVERAGE] and is_price_falling:
            return MacdVolumeEvidence.BEARISH_TREND_WITH_VOLUME_CONFIRM, 0.7
        elif (is_golden_cross or is_dead_cross) and volume_pattern != VolumePattern.BELOW_AVERAGE:
            return MacdVolumeEvidence.WEAK_SIGNAL, 0.3
        else:
            return MacdVolumeEvidence.NO_SIGNAL, 0.0
            
    except Exception as e:
        logger.error(f"MACD-거래량 조합 분석 실패: {e}")
        return MacdVolumeEvidence.NO_SIGNAL, 0.0


def get_volume_pattern(data: pd.DataFrame,
                      volume_column: str = 'Volume',
                      volume_sma_column: str = 'Volume_SMA_20',
                      volume_surge_factor: float = 1.5,
                      min_trend_days: int = 3) -> VolumePattern:
    """
    거래량 패턴을 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        volume_column: 거래량 컬럼명
        volume_sma_column: 거래량 이동평균 컬럼명
        volume_surge_factor: 거래량 급증 임계값
        min_trend_days: 최소 추세 확인 일수
        
    Returns:
        VolumePattern: 거래량 패턴
    """
    try:
        if len(data) < min_trend_days:
            return VolumePattern.NEUTRAL
            
        latest = data.iloc[-1]
        volume_ratio = latest[volume_column] / latest[volume_sma_column]
        
        # 거래량 급증
        if volume_ratio > volume_surge_factor:
            return VolumePattern.SURGE
        
        # 평균 이상 거래량
        if volume_ratio > 1.1:
            return VolumePattern.ABOVE_AVERAGE
        
        # 평균 이하 거래량
        if volume_ratio < 0.8:
            return VolumePattern.BELOW_AVERAGE
        
        # 거래량 감소 추세 확인
        if len(data) >= min_trend_days + 1:
            recent_volumes = data[volume_column].iloc[-min_trend_days:].values
            if all(recent_volumes[i] < recent_volumes[i-1] for i in range(1, len(recent_volumes))):
                return VolumePattern.DECLINING
        
        return VolumePattern.NEUTRAL
        
    except Exception as e:
        logger.error(f"거래량 패턴 분석 실패: {e}")
        return VolumePattern.NEUTRAL


def calculate_volume_strength(data: pd.DataFrame,
                            volume_column: str = 'Volume',
                            volume_sma_column: str = 'Volume_SMA_20',
                            price_change_weight: float = 100.0) -> float:
    """
    거래량 강도를 계산합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        volume_column: 거래량 컬럼명
        volume_sma_column: 거래량 이동평균 컬럼명
        price_change_weight: 가격 변화 가중치
        
    Returns:
        float: 거래량 강도 (0.0 ~ 2.0)
    """
    try:
        if len(data) < 2:
            return 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 거래량 비율
        volume_ratio = latest[volume_column] / latest[volume_sma_column]
        volume_strength = min((volume_ratio - 1.0), 1.0)  # 최대 1.0
        
        # 가격 변화 강도
        price_change_pct = abs(latest['Close'] - prev['Close']) / prev['Close']
        price_strength = min(price_change_pct * price_change_weight, 1.0)  # 최대 1.0
        
        return volume_strength + price_strength
        
    except Exception as e:
        logger.error(f"거래량 강도 계산 실패: {e}")
        return 0.0


def analyze_volume_price_relationship(data: pd.DataFrame,
                                    volume_column: str = 'Volume',
                                    lookback_days: int = 5) -> Dict[str, float]:
    """
    거래량과 가격의 관계를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        volume_column: 거래량 컬럼명
        lookback_days: 분석 기간
        
    Returns:
        Dict[str, float]: 분석 결과
    """
    try:
        if len(data) < lookback_days + 1:
            return {"correlation": 0.0, "divergence_score": 0.0}
            
        recent_data = data.iloc[-lookback_days-1:]
        
        # 가격 변화율과 거래량 변화율 계산
        price_changes = recent_data['Close'].pct_change().fillna(0)
        volume_changes = recent_data[volume_column].pct_change().fillna(0)
        
        # 상관관계 계산
        correlation = price_changes.corr(volume_changes)
        if pd.isna(correlation):
            correlation = 0.0
        
        # 다이버전스 점수 계산 (가격과 거래량이 반대 방향일 때)
        divergence_score = 0.0
        for i in range(1, len(price_changes)):
            if (price_changes.iloc[i] > 0 and volume_changes.iloc[i] < 0) or \
               (price_changes.iloc[i] < 0 and volume_changes.iloc[i] > 0):
                divergence_score += abs(price_changes.iloc[i]) + abs(volume_changes.iloc[i])
        
        divergence_score = min(divergence_score / lookback_days, 1.0)
        
        return {
            "correlation": correlation,
            "divergence_score": divergence_score
        }
        
    except Exception as e:
        logger.error(f"거래량-가격 관계 분석 실패: {e}")
        return {"correlation": 0.0, "divergence_score": 0.0} 