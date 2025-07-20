"""
Momentum Analysis Module

RSI, Stochastic, MACD 등 모멘텀 지표들의 복합 분석 로직을 제공합니다.
기존 CompositeDetector에서 분리된 모멘텀 분석 함수들을 포함합니다.
"""

from enum import Enum
from typing import Dict, Optional, Tuple

import pandas as pd

from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MomentumConsensus(Enum):
    """모멘텀 컨센서스 분류"""
    STRONG_BULLISH = "강력한 매수 컨센서스"
    MODERATE_BULLISH = "보통 매수 컨센서스"
    WEAK_BULLISH = "약한 매수 컨센서스"
    NEUTRAL = "중립"
    WEAK_BEARISH = "약한 매도 컨센서스"
    MODERATE_BEARISH = "보통 매도 컨센서스"
    STRONG_BEARISH = "강력한 매도 컨센서스"


class RSIStochCondition(Enum):
    """RSI + Stochastic 조합 상태"""
    DOUBLE_OVERSOLD_EXIT = "이중 과매도 탈출"
    DOUBLE_OVERSOLD = "이중 과매도"
    DOUBLE_OVERBOUGHT_EXIT = "이중 과매수 탈출"
    DOUBLE_OVERBOUGHT = "이중 과매수"
    DIVERGENT = "분기"
    ALIGNED_BULLISH = "상승 일치"
    ALIGNED_BEARISH = "하락 일치"
    NEUTRAL = "중립"


def get_momentum_consensus(data: pd.DataFrame, 
                         rsi_column: str = 'RSI_14',
                         stoch_k_column: str = 'STOCHk_14_3_3',
                         stoch_d_column: str = 'STOCHd_14_3_3',
                         macd_column: str = 'MACD_12_26_9',
                         macd_signal_column: str = 'MACDs_12_26_9') -> MomentumConsensus:
    """
    RSI, Stochastic, MACD를 종합하여 모멘텀 컨센서스를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        rsi_column: RSI 컬럼명
        stoch_k_column: Stochastic %K 컬럼명
        stoch_d_column: Stochastic %D 컬럼명
        macd_column: MACD 컬럼명
        macd_signal_column: MACD Signal 컬럼명
        
    Returns:
        MomentumConsensus: 모멘텀 컨센서스 결과
    """
    try:
        if len(data) < 2:
            return MomentumConsensus.NEUTRAL
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 각 지표별 점수 계산 (-3 ~ +3)
        rsi_score = _calculate_rsi_momentum_score(latest[rsi_column], prev[rsi_column])
        stoch_score = _calculate_stoch_momentum_score(
            latest[stoch_k_column], latest[stoch_d_column],
            prev[stoch_k_column], prev[stoch_d_column]
        )
        macd_score = _calculate_macd_momentum_score(
            latest[macd_column], latest[macd_signal_column],
            prev[macd_column], prev[macd_signal_column]
        )
        
        # 총 점수 계산
        total_score = rsi_score + stoch_score + macd_score
        
        # 컨센서스 분류
        if total_score >= 7:
            return MomentumConsensus.STRONG_BULLISH
        elif total_score >= 4:
            return MomentumConsensus.MODERATE_BULLISH
        elif total_score >= 1:
            return MomentumConsensus.WEAK_BULLISH
        elif total_score <= -7:
            return MomentumConsensus.STRONG_BEARISH
        elif total_score <= -4:
            return MomentumConsensus.MODERATE_BEARISH
        elif total_score <= -1:
            return MomentumConsensus.WEAK_BEARISH
        else:
            return MomentumConsensus.NEUTRAL
            
    except Exception as e:
        logger.error(f"모멘텀 컨센서스 분석 실패: {e}")
        return MomentumConsensus.NEUTRAL


def analyze_rsi_stoch_condition(data: pd.DataFrame,
                              rsi_column: str = 'RSI_14',
                              stoch_k_column: str = 'STOCHk_14_3_3',
                              stoch_d_column: str = 'STOCHd_14_3_3') -> Tuple[RSIStochCondition, float]:
    """
    RSI와 Stochastic의 조합 상태를 분석합니다.
    
    Args:
        data: OHLCV 및 지표 데이터
        rsi_column: RSI 컬럼명
        stoch_k_column: Stochastic %K 컬럼명
        stoch_d_column: Stochastic %D 컬럼명
        
    Returns:
        Tuple[RSIStochCondition, float]: (상태, 신호 강도)
    """
    try:
        if len(data) < 2:
            return RSIStochCondition.NEUTRAL, 0.0
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        rsi_current = latest[rsi_column]
        rsi_prev = prev[rsi_column]
        stoch_k = latest[stoch_k_column]
        stoch_d = latest[stoch_d_column]
        stoch_k_prev = prev[stoch_k_column]
        stoch_d_prev = prev[stoch_d_column]
        
        # 과매도/과매수 상태 확인
        rsi_oversold = rsi_current <= 30
        rsi_oversold_prev = rsi_prev <= 30
        rsi_overbought = rsi_current >= 70
        rsi_overbought_prev = rsi_prev >= 70
        
        stoch_oversold = stoch_k <= 20
        stoch_overbought = stoch_k >= 80
        
        # 크로스 확인
        stoch_golden_cross = stoch_k_prev < stoch_d_prev and stoch_k > stoch_d
        stoch_dead_cross = stoch_k_prev > stoch_d_prev and stoch_k < stoch_d
        
        # 조합 상태 분석
        if rsi_oversold_prev and not rsi_oversold and stoch_oversold and stoch_golden_cross:
            return RSIStochCondition.DOUBLE_OVERSOLD_EXIT, 1.0
        elif rsi_oversold and stoch_oversold:
            return RSIStochCondition.DOUBLE_OVERSOLD, 0.8
        elif rsi_overbought_prev and not rsi_overbought and stoch_overbought and stoch_dead_cross:
            return RSIStochCondition.DOUBLE_OVERBOUGHT_EXIT, 1.0
        elif rsi_overbought and stoch_overbought:
            return RSIStochCondition.DOUBLE_OVERBOUGHT, 0.8
        elif rsi_current > 50 and stoch_k > stoch_d and stoch_k > 50:
            return RSIStochCondition.ALIGNED_BULLISH, 0.6
        elif rsi_current < 50 and stoch_k < stoch_d and stoch_k < 50:
            return RSIStochCondition.ALIGNED_BEARISH, 0.6
        else:
            return RSIStochCondition.NEUTRAL, 0.0
            
    except Exception as e:
        logger.error(f"RSI-Stoch 조합 분석 실패: {e}")
        return RSIStochCondition.NEUTRAL, 0.0


def _calculate_rsi_momentum_score(rsi_current: float, rsi_prev: float) -> int:
    """RSI 모멘텀 점수 계산 (-3 ~ +3)"""
    # 과매도 탈출
    if rsi_prev <= 30 < rsi_current:
        return 3
    # 과매수 탈출
    elif rsi_prev >= 70 > rsi_current:
        return -3
    # 과매도 지속
    elif rsi_current <= 30:
        return 2
    # 과매수 지속
    elif rsi_current >= 70:
        return -2
    # 상승 모멘텀
    elif rsi_current > rsi_prev and rsi_current > 55:
        return 1
    # 하락 모멘텀
    elif rsi_current < rsi_prev and rsi_current < 45:
        return -1
    else:
        return 0


def _calculate_stoch_momentum_score(stoch_k: float, stoch_d: float, 
                                  stoch_k_prev: float, stoch_d_prev: float) -> int:
    """Stochastic 모멘텀 점수 계산 (-3 ~ +3)"""
    # 골든 크로스
    if stoch_k_prev < stoch_d_prev and stoch_k > stoch_d:
        if stoch_k < 30:  # 과매도 구간에서 골든크로스
            return 3
        else:
            return 2
    # 데드 크로스
    elif stoch_k_prev > stoch_d_prev and stoch_k < stoch_d:
        if stoch_k > 70:  # 과매수 구간에서 데드크로스
            return -3
        else:
            return -2
    # 과매도 반등
    elif stoch_k < 20 and stoch_k > stoch_k_prev:
        return 1
    # 과매수 하락
    elif stoch_k > 80 and stoch_k < stoch_k_prev:
        return -1
    else:
        return 0


def _calculate_macd_momentum_score(macd: float, macd_signal: float,
                                 macd_prev: float, macd_signal_prev: float) -> int:
    """MACD 모멘텀 점수 계산 (-3 ~ +3)"""
    # 골든 크로스
    if macd_prev < macd_signal_prev and macd > macd_signal:
        if macd > 0:  # 0선 위에서 골든크로스
            return 3
        else:
            return 2
    # 데드 크로스
    elif macd_prev > macd_signal_prev and macd < macd_signal:
        if macd < 0:  # 0선 아래에서 데드크로스
            return -3
        else:
            return -2
    # 상승 지속
    elif macd > macd_signal and macd > macd_prev:
        return 1
    # 하락 지속
    elif macd < macd_signal and macd < macd_prev:
        return -1
    else:
        return 0 