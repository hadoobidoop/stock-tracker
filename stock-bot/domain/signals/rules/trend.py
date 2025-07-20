"""
Trend Rules Module

추세 관련 규칙 함수들을 정의합니다.
analysis/trend.py의 함수들을 활용하여 규칙을 만듭니다.
"""

from ..analysis.trend import (
    analyze_macd_cross,
    analyze_sma_trend,
    get_trend_strength,
    analyze_trend_alignment,
    MacdEvidence,
    SmaTrendEvidence,
    TrendStrength
)

# 추세 관련 규칙들
TREND_RULES = {
    # MACD 골든크로스 확인
    'macd_confirms_golden_cross':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.GOLDEN_CROSS,
    
    # MACD 데드크로스 확인
    'macd_confirms_dead_cross':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.DEAD_CROSS,
    
    # MACD 상승 추세 확인
    'macd_confirms_bullish_trend':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.BULLISH_TREND,
    
    # MACD 하락 추세 확인
    'macd_confirms_bearish_trend':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.BEARISH_TREND,
    
    # MACD 상승 반전 확인
    'macd_confirms_bullish_reversal':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.BULLISH_REVERSAL,
    
    # MACD 하락 반전 확인
    'macd_confirms_bearish_reversal':
        lambda data: analyze_macd_cross(data)[0] == MacdEvidence.BEARISH_REVERSAL,
    
    # SMA 골든크로스 확인
    'sma_confirms_golden_cross':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.GOLDEN_CROSS,
    
    # SMA 데드크로스 확인
    'sma_confirms_dead_cross':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.DEAD_CROSS,
    
    # SMA 상승 정배열 확인
    'sma_confirms_bullish_alignment':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.BULLISH_ALIGNMENT,
    
    # SMA 하락 정배열 확인
    'sma_confirms_bearish_alignment':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.BEARISH_ALIGNMENT,
    
    # SMA 추세 지속 확인
    'sma_confirms_trend_continuation':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.TREND_CONTINUATION,
    
    # SMA 추세 반전 확인
    'sma_confirms_trend_reversal':
        lambda data: analyze_sma_trend(data)[0] == SmaTrendEvidence.TREND_REVERSAL,
    
    # 매우 강한 추세 확인
    'trend_strength_very_strong':
        lambda data: get_trend_strength(data) == TrendStrength.VERY_STRONG,
    
    # 강한 추세 확인
    'trend_strength_strong':
        lambda data: get_trend_strength(data) == TrendStrength.STRONG,
    
    # 보통 추세 확인
    'trend_strength_moderate':
        lambda data: get_trend_strength(data) == TrendStrength.MODERATE,
    
    # 약한 추세 확인
    'trend_strength_weak':
        lambda data: get_trend_strength(data) == TrendStrength.WEAK,
    
    # 매우 약한 추세 확인
    'trend_strength_very_weak':
        lambda data: get_trend_strength(data) == TrendStrength.VERY_WEAK,
    
    # 추세 일치도 높음
    'trend_alignment_high':
        lambda data: analyze_trend_alignment(data)['alignment_score'] > 0.7,
    
    # 추세 일치도 보통
    'trend_alignment_moderate':
        lambda data: 0.3 < analyze_trend_alignment(data)['alignment_score'] <= 0.7,
    
    # 추세 일치도 낮음
    'trend_alignment_low':
        lambda data: analyze_trend_alignment(data)['alignment_score'] <= 0.3,
    
    # 추세 일관성 높음
    'trend_consistency_high':
        lambda data: analyze_trend_alignment(data)['trend_consistency'] > 0.8,
    
    # 추세 일관성 보통
    'trend_consistency_moderate':
        lambda data: 0.5 < analyze_trend_alignment(data)['trend_consistency'] <= 0.8,
    
    # 추세 일관성 낮음
    'trend_consistency_low':
        lambda data: analyze_trend_alignment(data)['trend_consistency'] <= 0.5,
    
    # ADX 강한 추세 (25 이상)
    'adx_strong_trend':
        lambda data: len(data) > 0 and data.iloc[-1].get('ADX_14', 0) >= 25,
    
    # ADX 약한 추세 (20 이상)
    'adx_weak_trend':
        lambda data: len(data) > 0 and data.iloc[-1].get('ADX_14', 0) >= 20,
    
    # ADX 추세 강화
    'adx_trend_strengthening':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('ADX_14', 0) > data.iloc[-2].get('ADX_14', 0)),
    
    # ADX 추세 약화
    'adx_trend_weakening':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('ADX_14', 0) < data.iloc[-2].get('ADX_14', 0)),
    
    # SMA 단기 > 장기
    'sma_short_above_long':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('SMA_5', 0) > data.iloc[-1].get('SMA_20', 0)),
    
    # SMA 단기 < 장기
    'sma_short_below_long':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('SMA_5', 0) < data.iloc[-1].get('SMA_20', 0)),
    
    # SMA 단기 상승
    'sma_short_rising':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('SMA_5', 0) > data.iloc[-2].get('SMA_5', 0)),
    
    # SMA 단기 하락
    'sma_short_falling':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('SMA_5', 0) < data.iloc[-2].get('SMA_5', 0)),
    
    # SMA 장기 상승
    'sma_long_rising':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('SMA_20', 0) > data.iloc[-2].get('SMA_20', 0)),
    
    # SMA 장기 하락
    'sma_long_falling':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('SMA_20', 0) < data.iloc[-2].get('SMA_20', 0)),
} 