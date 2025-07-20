"""
Volatility Analysis Module

BB(볼린저밴드), ADX 등 변동성 지표들의 복합 분석 로직을 제공합니다.
기존 CompositeDetector에서 분리된 변동성 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Tuple

import pandas as pd

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BBEvidence(Enum):
    """볼린저밴드 근거"""
    SQUEEZE_BREAKOUT_UP = "BB Squeeze 후 상단 돌파"
    SQUEEZE_BREAKOUT_DOWN = "BB Squeeze 후 하단 돌파"
    UPPER_BAND_TOUCH = "BB 상단 터치"
    LOWER_BAND_TOUCH = "BB 하단 터치"
    MEAN_REVERSION_UP = "BB 평균 회귀 상승"
    MEAN_REVERSION_DOWN = "BB 평균 회귀 하락"
    NEUTRAL = "BB 중립"


class ADXEvidence(Enum):
    """ADX 근거"""
    STRONG_TREND_UP = "ADX 강한 상승 추세"
    STRONG_TREND_DOWN = "ADX 강한 하락 추세"
    WEAK_TREND_UP = "ADX 약한 상승 추세"
    WEAK_TREND_DOWN = "ADX 약한 하락 추세"
    TREND_STRENGTHENING = "ADX 추세 강화"
    TREND_WEAKENING = "ADX 추세 약화"
    NEUTRAL = "ADX 중립"


class VolatilityPattern(Enum):
    """변동성 패턴 분류"""
    HIGH_VOLATILITY = "고변동성"
    LOW_VOLATILITY = "저변동성"
    INCREASING_VOLATILITY = "변동성 증가"
    DECREASING_VOLATILITY = "변동성 감소"
    SQUEEZE = "변동성 압축"
    EXPANSION = "변동성 확장"
    NEUTRAL = "중립"


def analyze_bb_volatility(data: pd.DataFrame,
                         bb_lower_column: str = 'BBL_20_2.0',
                         bb_middle_column: str = 'BBM_20_2.0',
                         bb_upper_column: str = 'BBU_20_2.0',
                         bb_bandwidth_column: str = 'BBB_20_2.0',
                         analysis_type: str = 'breakout') -> Tuple[BBEvidence, float]:
    """
    볼린저밴드 변동성을 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_lower_column: BB 하단 컬럼명
        bb_middle_column: BB 중간 컬럼명
        bb_upper_column: BB 상단 컬럼명
        bb_bandwidth_column: BB 밴드폭 컬럼명
        analysis_type: 분석 타입 ('breakout' 또는 'mean_reversion')
        
    Returns:
        Tuple[BBEvidence, float]: (근거, 신호 강도)
    """
    try:
        if len(data) < 3:
            return BBEvidence.NEUTRAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        prev2 = data.iloc[-3]
        
        current_price = latest['Close']
        bb_lower = latest[bb_lower_column]
        bb_middle = latest[bb_middle_column]
        bb_upper = latest[bb_upper_column]
        bb_bandwidth = latest[bb_bandwidth_column]
        
        # Squeeze 상태 확인 (밴드폭이 좁은 상태)
        avg_bandwidth = data[bb_bandwidth_column].rolling(20).mean().iloc[-1]
        is_squeezed = bb_bandwidth < avg_bandwidth * 0.8
        
        if analysis_type == 'breakout':
            return _analyze_bb_breakout(current_price, bb_lower, bb_upper, bb_bandwidth, 
                                      prev['Close'], prev[bb_upper_column], prev[bb_lower_column],
                                      is_squeezed)
        else:  # mean_reversion
            return _analyze_bb_mean_reversion(current_price, bb_lower, bb_middle, bb_upper,
                                            prev['Close'], prev[bb_lower_column], prev[bb_upper_column])
            
    except Exception as e:
        logger.error(f"BB 변동성 분석 실패: {e}")
        return BBEvidence.NEUTRAL, 0.0


def analyze_adx_trend(data: pd.DataFrame,
                     adx_column: str = 'ADX_14',
                     dmp_column: str = 'DMP_14',
                     dmn_column: str = 'DMN_14') -> Tuple[ADXEvidence, float]:
    """
    ADX 추세 강도를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        adx_column: ADX 컬럼명
        dmp_column: +DI 컬럼명
        dmn_column: -DI 컬럼명
        
    Returns:
        Tuple[ADXEvidence, float]: (근거, 신호 강도)
    """
    try:
        if len(data) < 2:
            return ADXEvidence.NEUTRAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        adx_current = latest[adx_column]
        adx_prev = prev[adx_column]
        dmp = latest.get(dmp_column, 0)
        dmn = latest.get(dmn_column, 0)
        
        # ADX 강도 분석
        if adx_current >= 25:
            if dmp > dmn:
                return ADXEvidence.STRONG_TREND_UP, 1.0
            else:
                return ADXEvidence.STRONG_TREND_DOWN, 1.0
        elif adx_current >= 20:
            if dmp > dmn:
                return ADXEvidence.WEAK_TREND_UP, 0.7
            else:
                return ADXEvidence.WEAK_TREND_DOWN, 0.7
        else:
            # 추세 강화/약화 확인
            if adx_current > adx_prev:
                return ADXEvidence.TREND_STRENGTHENING, 0.5
            elif adx_current < adx_prev:
                return ADXEvidence.TREND_WEAKENING, 0.3
            else:
                return ADXEvidence.NEUTRAL, 0.0
                
    except Exception as e:
        logger.error(f"ADX 추세 분석 실패: {e}")
        return ADXEvidence.NEUTRAL, 0.0


def get_volatility_pattern(data: pd.DataFrame,
                          bb_bandwidth_column: str = 'BBB_20_2.0',
                          lookback_periods: int = 20) -> VolatilityPattern:
    """
    변동성 패턴을 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_bandwidth_column: BB 밴드폭 컬럼명
        lookback_periods: 분석 기간
        
    Returns:
        VolatilityPattern: 변동성 패턴
    """
    try:
        if len(data) < lookback_periods + 1:
            return VolatilityPattern.NEUTRAL
            
        recent_data = data[bb_bandwidth_column].iloc[-lookback_periods:]
        current_bandwidth = recent_data.iloc[-1]
        avg_bandwidth = recent_data.mean()
        min_bandwidth = recent_data.min()
        max_bandwidth = recent_data.max()
        
        # Squeeze 상태 (밴드폭이 매우 좁음)
        if current_bandwidth < avg_bandwidth * 0.7:
            return VolatilityPattern.SQUEEZE
        
        # 고변동성 상태
        if current_bandwidth > avg_bandwidth * 1.3:
            return VolatilityPattern.HIGH_VOLATILITY
        
        # 저변동성 상태
        if current_bandwidth < avg_bandwidth * 0.8:
            return VolatilityPattern.LOW_VOLATILITY
        
        # 변동성 증가/감소 추세
        recent_trend = recent_data.iloc[-5:].pct_change().mean()
        if recent_trend > 0.05:
            return VolatilityPattern.INCREASING_VOLATILITY
        elif recent_trend < -0.05:
            return VolatilityPattern.DECREASING_VOLATILITY
        
        return VolatilityPattern.NEUTRAL
        
    except Exception as e:
        logger.error(f"변동성 패턴 분석 실패: {e}")
        return VolatilityPattern.NEUTRAL


def analyze_bb_adx_combination(data: pd.DataFrame,
                              bb_lower_column: str = 'BBL_20_2.0',
                              bb_upper_column: str = 'BBU_20_2.0',
                              bb_bandwidth_column: str = 'BBB_20_2.0',
                              adx_column: str = 'ADX_14',
                              dmp_column: str = 'DMP_14',
                              dmn_column: str = 'DMN_14') -> Dict[str, any]:
    """
    BB와 ADX의 조합을 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_lower_column: BB 하단 컬럼명
        bb_upper_column: BB 상단 컬럼명
        bb_bandwidth_column: BB 밴드폭 컬럼명
        adx_column: ADX 컬럼명
        dmp_column: +DI 컬럼명
        dmn_column: -DI 컬럼명
        
    Returns:
        Dict[str, any]: 조합 분석 결과
    """
    try:
        if len(data) < 2:
            return {"signal": "분석 불가", "strength": 0.0, "evidence": []}
            
        # 개별 분석 수행
        bb_evidence, bb_strength = analyze_bb_volatility(data, bb_lower_column, bb_middle_column, 
                                                        bb_upper_column, bb_bandwidth_column)
        adx_evidence, adx_strength = analyze_adx_trend(data, adx_column, dmp_column, dmn_column)
        volatility_pattern = get_volatility_pattern(data, bb_bandwidth_column)
        
        # 조합 신호 생성
        combined_strength = (bb_strength + adx_strength) / 2
        evidences = [bb_evidence.value, adx_evidence.value, volatility_pattern.value]
        
        # 신호 방향 결정
        if bb_evidence in [BBEvidence.SQUEEZE_BREAKOUT_UP, BBEvidence.MEAN_REVERSION_UP] and \
           adx_evidence in [ADXEvidence.STRONG_TREND_UP, ADXEvidence.WEAK_TREND_UP]:
            signal = "강한 매수 신호"
        elif bb_evidence in [BBEvidence.SQUEEZE_BREAKOUT_DOWN, BBEvidence.MEAN_REVERSION_DOWN] and \
             adx_evidence in [ADXEvidence.STRONG_TREND_DOWN, ADXEvidence.WEAK_TREND_DOWN]:
            signal = "강한 매도 신호"
        elif bb_evidence in [BBEvidence.SQUEEZE_BREAKOUT_UP, BBEvidence.MEAN_REVERSION_UP]:
            signal = "약한 매수 신호"
        elif bb_evidence in [BBEvidence.SQUEEZE_BREAKOUT_DOWN, BBEvidence.MEAN_REVERSION_DOWN]:
            signal = "약한 매도 신호"
        else:
            signal = "중립"
            combined_strength *= 0.5
        
        return {
            "signal": signal,
            "strength": combined_strength,
            "evidence": evidences,
            "bb_evidence": bb_evidence.value,
            "adx_evidence": adx_evidence.value,
            "volatility_pattern": volatility_pattern.value
        }
        
    except Exception as e:
        logger.error(f"BB-ADX 조합 분석 실패: {e}")
        return {"signal": "분석 실패", "strength": 0.0, "evidence": []}


def calculate_volatility_strength(data: pd.DataFrame,
                                bb_bandwidth_column: str = 'BBB_20_2.0',
                                lookback_periods: int = 20) -> float:
    """
    변동성 강도를 계산합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        bb_bandwidth_column: BB 밴드폭 컬럼명
        lookback_periods: 분석 기간
        
    Returns:
        float: 변동성 강도 (0.0 ~ 2.0)
    """
    try:
        if len(data) < lookback_periods:
            return 0.0
            
        recent_bandwidth = data[bb_bandwidth_column].iloc[-lookback_periods:]
        current_bandwidth = recent_bandwidth.iloc[-1]
        avg_bandwidth = recent_bandwidth.mean()
        
        # 변동성 강도 계산
        volatility_ratio = current_bandwidth / avg_bandwidth
        
        if volatility_ratio > 1.5:
            return 2.0  # 매우 높은 변동성
        elif volatility_ratio > 1.2:
            return 1.5  # 높은 변동성
        elif volatility_ratio > 0.8:
            return 1.0  # 보통 변동성
        elif volatility_ratio > 0.5:
            return 0.5  # 낮은 변동성
        else:
            return 0.0  # 매우 낮은 변동성
            
    except Exception as e:
        logger.error(f"변동성 강도 계산 실패: {e}")
        return 0.0


def _analyze_bb_breakout(current_price: float, bb_lower: float, bb_upper: float, bb_bandwidth: float,
                        prev_price: float, prev_bb_upper: float, prev_bb_lower: float,
                        is_squeezed: bool) -> Tuple[BBEvidence, float]:
    """BB 돌파 분석"""
    # 상단 돌파
    if prev_price < prev_bb_upper and current_price > bb_upper:
        strength = 1.0 if is_squeezed else 0.7
        return BBEvidence.SQUEEZE_BREAKOUT_UP, strength
    
    # 하단 돌파
    elif prev_price > prev_bb_lower and current_price < bb_lower:
        strength = 1.0 if is_squeezed else 0.7
        return BBEvidence.SQUEEZE_BREAKOUT_DOWN, strength
    
    # 상단 터치
    elif current_price >= bb_upper:
        return BBEvidence.UPPER_BAND_TOUCH, 0.5
    
    # 하단 터치
    elif current_price <= bb_lower:
        return BBEvidence.LOWER_BAND_TOUCH, 0.5
    
    else:
        return BBEvidence.NEUTRAL, 0.0


def _analyze_bb_mean_reversion(current_price: float, bb_lower: float, bb_middle: float, bb_upper: float,
                              prev_price: float, prev_bb_lower: float, prev_bb_upper: float) -> Tuple[BBEvidence, float]:
    """BB 평균 회귀 분석"""
    # 하단에서 평균으로 회귀
    if prev_price < prev_bb_lower and current_price > bb_lower:
        strength = (current_price - bb_lower) / (bb_middle - bb_lower)
        return BBEvidence.MEAN_REVERSION_UP, min(strength, 1.0)
    
    # 상단에서 평균으로 회귀
    elif prev_price > prev_bb_upper and current_price < bb_upper:
        strength = (bb_upper - current_price) / (bb_upper - bb_middle)
        return BBEvidence.MEAN_REVERSION_DOWN, min(strength, 1.0)
    
    # 하단 근처에서 반등
    elif current_price <= bb_lower:
        return BBEvidence.LOWER_BAND_TOUCH, 0.6
    
    # 상단 근처에서 하락
    elif current_price >= bb_upper:
        return BBEvidence.UPPER_BAND_TOUCH, 0.6
    
    else:
        return BBEvidence.NEUTRAL, 0.0 