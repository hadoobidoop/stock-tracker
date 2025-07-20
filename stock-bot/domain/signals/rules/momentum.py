"""
Momentum Rules Module

모멘텀 관련 규칙 함수들을 정의합니다.
analysis/momentum.py의 함수들을 활용하여 규칙을 만듭니다.
"""

from ..analysis.momentum import (
    get_momentum_consensus,
    analyze_rsi_stoch_condition,
    MomentumConsensus,
    RSIStochCondition
)

# 모멘텀 관련 규칙들
MOMENTUM_RULES = {
    # 강한 매수 모멘텀 컨센서스
    'strong_bullish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.STRONG_BULLISH,
    
    # 보통 매수 모멘텀 컨센서스
    'moderate_bullish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.MODERATE_BULLISH,
    
    # 약한 매수 모멘텀 컨센서스
    'weak_bullish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.WEAK_BULLISH,
    
    # 강한 매도 모멘텀 컨센서스
    'strong_bearish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.STRONG_BEARISH,
    
    # 보통 매도 모멘텀 컨센서스
    'moderate_bearish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.MODERATE_BEARISH,
    
    # 약한 매도 모멘텀 컨센서스
    'weak_bearish_momentum_consensus': 
        lambda data: get_momentum_consensus(data) == MomentumConsensus.WEAK_BEARISH,
    
    # RSI-Stoch 이중 과매도 탈출
    'rsi_stoch_double_oversold_exit': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.DOUBLE_OVERSOLD_EXIT,
    
    # RSI-Stoch 이중 과매도
    'rsi_stoch_double_oversold': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.DOUBLE_OVERSOLD,
    
    # RSI-Stoch 이중 과매수 탈출
    'rsi_stoch_double_overbought_exit': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.DOUBLE_OVERBOUGHT_EXIT,
    
    # RSI-Stoch 이중 과매수
    'rsi_stoch_double_overbought': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.DOUBLE_OVERBOUGHT,
    
    # RSI-Stoch 상승 일치
    'rsi_stoch_aligned_bullish': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.ALIGNED_BULLISH,
    
    # RSI-Stoch 하락 일치
    'rsi_stoch_aligned_bearish': 
        lambda data: analyze_rsi_stoch_condition(data)[0] == RSIStochCondition.ALIGNED_BEARISH,
    
    # RSI 과매도 상태
    'rsi_oversold': 
        lambda data: len(data) > 0 and data.iloc[-1].get('RSI_14', 50) <= 30,
    
    # RSI 과매수 상태
    'rsi_overbought': 
        lambda data: len(data) > 0 and data.iloc[-1].get('RSI_14', 50) >= 70,
    
    # RSI 과매도 탈출
    'rsi_oversold_exit': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('RSI_14', 50) <= 30 and 
                     data.iloc[-1].get('RSI_14', 50) > 30),
    
    # RSI 과매수 탈출
    'rsi_overbought_exit': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('RSI_14', 50) >= 70 and 
                     data.iloc[-1].get('RSI_14', 50) < 70),
    
    # Stochastic 과매도 상태
    'stoch_oversold': 
        lambda data: len(data) > 0 and data.iloc[-1].get('STOCHk_14_3_3', 50) <= 20,
    
    # Stochastic 과매수 상태
    'stoch_overbought': 
        lambda data: len(data) > 0 and data.iloc[-1].get('STOCHk_14_3_3', 50) >= 80,
    
    # Stochastic 골든크로스
    'stoch_golden_cross': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('STOCHk_14_3_3', 50) < data.iloc[-2].get('STOCHd_14_3_3', 50) and
                     data.iloc[-1].get('STOCHk_14_3_3', 50) > data.iloc[-1].get('STOCHd_14_3_3', 50)),
    
    # Stochastic 데드크로스
    'stoch_dead_cross': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('STOCHk_14_3_3', 50) > data.iloc[-2].get('STOCHd_14_3_3', 50) and
                     data.iloc[-1].get('STOCHk_14_3_3', 50) < data.iloc[-1].get('STOCHd_14_3_3', 50)),
    
    # MACD 골든크로스
    'macd_golden_cross': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('MACD_12_26_9', 0) < data.iloc[-2].get('MACDs_12_26_9', 0) and
                     data.iloc[-1].get('MACD_12_26_9', 0) > data.iloc[-1].get('MACDs_12_26_9', 0)),
    
    # MACD 데드크로스
    'macd_dead_cross': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('MACD_12_26_9', 0) > data.iloc[-2].get('MACDs_12_26_9', 0) and
                     data.iloc[-1].get('MACD_12_26_9', 0) < data.iloc[-1].get('MACDs_12_26_9', 0)),
    
    # MACD 0선 상향 돌파
    'macd_zero_line_cross_up': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('MACD_12_26_9', 0) <= 0 and
                     data.iloc[-1].get('MACD_12_26_9', 0) > 0),
    
    # MACD 0선 하향 돌파
    'macd_zero_line_cross_down': 
        lambda data: (len(data) > 1 and 
                     data.iloc[-2].get('MACD_12_26_9', 0) >= 0 and
                     data.iloc[-1].get('MACD_12_26_9', 0) < 0),
    
    # MACD 상승 추세
    'macd_bullish_trend': 
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('MACD_12_26_9', 0) > data.iloc[-1].get('MACDs_12_26_9', 0)),
    
    # MACD 하락 추세
    'macd_bearish_trend': 
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('MACD_12_26_9', 0) < data.iloc[-1].get('MACDs_12_26_9', 0)),
} 