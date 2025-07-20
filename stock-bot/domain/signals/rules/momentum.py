"""
Momentum Rules Module

모멘텀 지표(RSI, Stochastic, MACD) 기반 거래 규칙들을 정의합니다.
analysis.momentum 모듈의 함수들을 활용하여 재사용 가능한 규칙을 제공합니다.
"""

import pandas as pd
from typing import Callable

from ..analysis.momentum import (
    get_momentum_consensus, 
    analyze_rsi_stoch_condition,
    MomentumConsensus,
    RSIStochCondition
)


def rsi_stoch_oversold_consensus(data: pd.DataFrame) -> bool:
    """RSI와 Stochastic이 모두 과매도에서 탈출하는 강한 매수 컨센서스"""
    condition = analyze_rsi_stoch_condition(data)
    return condition == RSIStochCondition.DOUBLE_OVERSOLD_EXIT


def rsi_stoch_overbought_consensus(data: pd.DataFrame) -> bool:
    """RSI와 Stochastic이 모두 과매수에서 탈출하는 강한 매도 컨센서스"""
    condition = analyze_rsi_stoch_condition(data)
    return condition == RSIStochCondition.DOUBLE_OVERBOUGHT_EXIT


def strong_bullish_momentum_consensus(data: pd.DataFrame) -> bool:
    """RSI, Stochastic, MACD가 모두 동의하는 강력한 매수 모멘텀"""
    consensus = get_momentum_consensus(data)
    return consensus == MomentumConsensus.STRONG_BULLISH


def strong_bearish_momentum_consensus(data: pd.DataFrame) -> bool:
    """RSI, Stochastic, MACD가 모두 동의하는 강력한 매도 모멘텀"""
    consensus = get_momentum_consensus(data)
    return consensus == MomentumConsensus.STRONG_BEARISH


def moderate_bullish_momentum_consensus(data: pd.DataFrame) -> bool:
    """보통 수준의 매수 모멘텀 컨센서스"""
    consensus = get_momentum_consensus(data)
    return consensus in [MomentumConsensus.STRONG_BULLISH, MomentumConsensus.MODERATE_BULLISH]


def moderate_bearish_momentum_consensus(data: pd.DataFrame) -> bool:
    """보통 수준의 매도 모멘텀 컨센서스"""
    consensus = get_momentum_consensus(data)
    return consensus in [MomentumConsensus.STRONG_BEARISH, MomentumConsensus.MODERATE_BEARISH]


def rsi_oversold_recovery(data: pd.DataFrame, rsi_column: str = 'RSI_14') -> bool:
    """RSI 과매도에서 회복 신호"""
    if len(data) < 2 or rsi_column not in data.columns:
        return False
    
    current_rsi = data[rsi_column].iloc[-1]
    prev_rsi = data[rsi_column].iloc[-2]
    
    # 이전에 과매도(30 이하)였고 현재 30을 돌파
    return prev_rsi <= 30 and current_rsi > 30


def rsi_overbought_breakdown(data: pd.DataFrame, rsi_column: str = 'RSI_14') -> bool:
    """RSI 과매수에서 하락 신호"""
    if len(data) < 2 or rsi_column not in data.columns:
        return False
    
    current_rsi = data[rsi_column].iloc[-1]
    prev_rsi = data[rsi_column].iloc[-2]
    
    # 이전에 과매수(70 이상)였고 현재 70을 하회
    return prev_rsi >= 70 and current_rsi < 70


def stoch_oversold_recovery(data: pd.DataFrame, 
                          stoch_k_column: str = 'STOCHk_14_3_3',
                          stoch_d_column: str = 'STOCHd_14_3_3') -> bool:
    """Stochastic 과매도에서 회복 신호"""
    if len(data) < 2 or stoch_k_column not in data.columns or stoch_d_column not in data.columns:
        return False
    
    current_k = data[stoch_k_column].iloc[-1]
    current_d = data[stoch_d_column].iloc[-1]
    prev_k = data[stoch_k_column].iloc[-2]
    prev_d = data[stoch_d_column].iloc[-2]
    
    # 이전에 둘 다 과매도(20 이하)였고 현재 20을 돌파
    return (prev_k <= 20 and prev_d <= 20) and (current_k > 20 or current_d > 20)


def stoch_overbought_breakdown(data: pd.DataFrame,
                             stoch_k_column: str = 'STOCHk_14_3_3',
                             stoch_d_column: str = 'STOCHd_14_3_3') -> bool:
    """Stochastic 과매수에서 하락 신호"""
    if len(data) < 2 or stoch_k_column not in data.columns or stoch_d_column not in data.columns:
        return False
    
    current_k = data[stoch_k_column].iloc[-1]
    current_d = data[stoch_d_column].iloc[-1]
    prev_k = data[stoch_k_column].iloc[-2]
    prev_d = data[stoch_d_column].iloc[-2]
    
    # 이전에 둘 다 과매수(80 이상)였고 현재 80을 하회
    return (prev_k >= 80 and prev_d >= 80) and (current_k < 80 or current_d < 80)


def macd_bullish_crossover(data: pd.DataFrame,
                          macd_column: str = 'MACD_12_26_9',
                          macd_signal_column: str = 'MACDs_12_26_9') -> bool:
    """MACD 골든크로스 신호"""
    if len(data) < 2 or macd_column not in data.columns or macd_signal_column not in data.columns:
        return False
    
    current_macd = data[macd_column].iloc[-1]
    current_signal = data[macd_signal_column].iloc[-1]
    prev_macd = data[macd_column].iloc[-2]
    prev_signal = data[macd_signal_column].iloc[-2]
    
    # 이전에 MACD < Signal이었고 현재 MACD > Signal
    return prev_macd <= prev_signal and current_macd > current_signal


def macd_bearish_crossover(data: pd.DataFrame,
                          macd_column: str = 'MACD_12_26_9',
                          macd_signal_column: str = 'MACDs_12_26_9') -> bool:
    """MACD 데드크로스 신호"""
    if len(data) < 2 or macd_column not in data.columns or macd_signal_column not in data.columns:
        return False
    
    current_macd = data[macd_column].iloc[-1]
    current_signal = data[macd_signal_column].iloc[-1]
    prev_macd = data[macd_column].iloc[-2]
    prev_signal = data[macd_signal_column].iloc[-2]
    
    # 이전에 MACD > Signal이었고 현재 MACD < Signal
    return prev_macd >= prev_signal and current_macd < current_signal


# 모멘텀 규칙 딕셔너리
MOMENTUM_RULES = {
    # 복합 컨센서스 규칙
    'rsi_stoch_oversold_consensus': rsi_stoch_oversold_consensus,
    'rsi_stoch_overbought_consensus': rsi_stoch_overbought_consensus,
    'strong_bullish_momentum_consensus': strong_bullish_momentum_consensus,
    'strong_bearish_momentum_consensus': strong_bearish_momentum_consensus,
    'moderate_bullish_momentum_consensus': moderate_bullish_momentum_consensus,
    'moderate_bearish_momentum_consensus': moderate_bearish_momentum_consensus,
    
    # 개별 지표 규칙
    'rsi_oversold_recovery': rsi_oversold_recovery,
    'rsi_overbought_breakdown': rsi_overbought_breakdown,
    'stoch_oversold_recovery': stoch_oversold_recovery,
    'stoch_overbought_breakdown': stoch_overbought_breakdown,
    'macd_bullish_crossover': macd_bullish_crossover,
    'macd_bearish_crossover': macd_bearish_crossover,
} 