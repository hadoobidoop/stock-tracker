"""
Volatility Rules Module

변동성 관련 규칙 함수들을 정의합니다.
analysis/volatility.py의 함수들을 활용하여 규칙을 만듭니다.
"""

from ..analysis.volatility import (
    analyze_bb_volatility,
    analyze_adx_trend,
    get_volatility_pattern,
    analyze_bb_adx_combination,
    calculate_volatility_strength,
    BBEvidence,
    ADXEvidence,
    VolatilityPattern
)

# 변동성 관련 규칙들
VOLATILITY_RULES = {
    # BB Squeeze 후 상단 돌파
    'bb_squeeze_breakout_up':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.SQUEEZE_BREAKOUT_UP,
    
    # BB Squeeze 후 하단 돌파
    'bb_squeeze_breakout_down':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.SQUEEZE_BREAKOUT_DOWN,
    
    # BB 상단 터치
    'bb_upper_band_touch':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.UPPER_BAND_TOUCH,
    
    # BB 하단 터치
    'bb_lower_band_touch':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.LOWER_BAND_TOUCH,
    
    # BB 평균 회귀 상승
    'bb_mean_reversion_up':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.MEAN_REVERSION_UP,
    
    # BB 평균 회귀 하락
    'bb_mean_reversion_down':
        lambda data: analyze_bb_volatility(data)[0] == BBEvidence.MEAN_REVERSION_DOWN,
    
    # ADX 강한 상승 추세
    'adx_strong_trend_up':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.STRONG_TREND_UP,
    
    # ADX 강한 하락 추세
    'adx_strong_trend_down':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.STRONG_TREND_DOWN,
    
    # ADX 약한 상승 추세
    'adx_weak_trend_up':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.WEAK_TREND_UP,
    
    # ADX 약한 하락 추세
    'adx_weak_trend_down':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.WEAK_TREND_DOWN,
    
    # ADX 추세 강화
    'adx_trend_strengthening':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.TREND_STRENGTHENING,
    
    # ADX 추세 약화
    'adx_trend_weakening':
        lambda data: analyze_adx_trend(data)[0] == ADXEvidence.TREND_WEAKENING,
    
    # 고변동성 패턴
    'volatility_high_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.HIGH_VOLATILITY,
    
    # 저변동성 패턴
    'volatility_low_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.LOW_VOLATILITY,
    
    # 변동성 증가 패턴
    'volatility_increasing_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.INCREASING_VOLATILITY,
    
    # 변동성 감소 패턴
    'volatility_decreasing_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.DECREASING_VOLATILITY,
    
    # 변동성 압축 패턴
    'volatility_squeeze_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.SQUEEZE,
    
    # 변동성 확장 패턴
    'volatility_expansion_pattern':
        lambda data: get_volatility_pattern(data) == VolatilityPattern.EXPANSION,
    
    # 변동성 강도 높음
    'volatility_strength_high':
        lambda data: calculate_volatility_strength(data) > 1.5,
    
    # 변동성 강도 보통
    'volatility_strength_moderate':
        lambda data: 0.5 < calculate_volatility_strength(data) <= 1.5,
    
    # 변동성 강도 낮음
    'volatility_strength_low':
        lambda data: calculate_volatility_strength(data) <= 0.5,
    
    # BB-ADX 강한 매수 신호
    'bb_adx_strong_bullish':
        lambda data: analyze_bb_adx_combination(data)['signal'] == "강한 매수 신호",
    
    # BB-ADX 강한 매도 신호
    'bb_adx_strong_bearish':
        lambda data: analyze_bb_adx_combination(data)['signal'] == "강한 매도 신호",
    
    # BB-ADX 약한 매수 신호
    'bb_adx_weak_bullish':
        lambda data: analyze_bb_adx_combination(data)['signal'] == "약한 매수 신호",
    
    # BB-ADX 약한 매도 신호
    'bb_adx_weak_bearish':
        lambda data: analyze_bb_adx_combination(data)['signal'] == "약한 매도 신호",
    
    # BB 상단 밴드 위
    'bb_above_upper_band':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Close', 0) > data.iloc[-1].get('BBU_20_2.0', 0)),
    
    # BB 하단 밴드 아래
    'bb_below_lower_band':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Close', 0) < data.iloc[-1].get('BBL_20_2.0', 0)),
    
    # BB 중간선 위
    'bb_above_middle_band':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Close', 0) > data.iloc[-1].get('BBM_20_2.0', 0)),
    
    # BB 중간선 아래
    'bb_below_middle_band':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Close', 0) < data.iloc[-1].get('BBM_20_2.0', 0)),
    
    # BB 밴드폭 좁음 (Squeeze)
    'bb_bandwidth_narrow':
        lambda data: (len(data) > 20 and 
                     data.iloc[-1].get('BBB_20_2.0', 0) < data['BBB_20_2.0'].rolling(20).mean().iloc[-1] * 0.8),
    
    # BB 밴드폭 넓음 (Expansion)
    'bb_bandwidth_wide':
        lambda data: (len(data) > 20 and 
                     data.iloc[-1].get('BBB_20_2.0', 0) > data['BBB_20_2.0'].rolling(20).mean().iloc[-1] * 1.2),
    
    # ADX 25 이상 (강한 추세)
    'adx_above_25':
        lambda data: len(data) > 0 and data.iloc[-1].get('ADX_14', 0) >= 25,
    
    # ADX 20 이상 (약한 추세)
    'adx_above_20':
        lambda data: len(data) > 0 and data.iloc[-1].get('ADX_14', 0) >= 20,
    
    # ADX 15 이하 (약한 추세)
    'adx_below_15':
        lambda data: len(data) > 0 and data.iloc[-1].get('ADX_14', 0) <= 15,
    
    # ADX 상승 중
    'adx_rising':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('ADX_14', 0) > data.iloc[-2].get('ADX_14', 0)),
    
    # ADX 하락 중
    'adx_falling':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('ADX_14', 0) < data.iloc[-2].get('ADX_14', 0)),
    
    # +DI > -DI (상승 추세)
    'di_plus_above_minus':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('DMP_14', 0) > data.iloc[-1].get('DMN_14', 0)),
    
    # +DI < -DI (하락 추세)
    'di_plus_below_minus':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('DMP_14', 0) < data.iloc[-1].get('DMN_14', 0)),
    
    # BB Squeeze + ADX 강세
    'bb_squeeze_with_strong_adx':
        lambda data: (len(data) > 20 and 
                     data.iloc[-1].get('BBB_20_2.0', 0) < data['BBB_20_2.0'].rolling(20).mean().iloc[-1] * 0.8 and
                     data.iloc[-1].get('ADX_14', 0) >= 25),
    
    # BB Expansion + ADX 약세
    'bb_expansion_with_weak_adx':
        lambda data: (len(data) > 20 and 
                     data.iloc[-1].get('BBB_20_2.0', 0) > data['BBB_20_2.0'].rolling(20).mean().iloc[-1] * 1.2 and
                     data.iloc[-1].get('ADX_14', 0) <= 20),
    
    # BB 상단 돌파 + 거래량 급증
    'bb_upper_breakout_with_volume_surge':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Close', 0) > data.iloc[-1].get('BBU_20_2.0', 0) and
                     data.iloc[-2].get('Close', 0) <= data.iloc[-2].get('BBU_20_2.0', 0) and
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.5),
    
    # BB 하단 돌파 + 거래량 급증
    'bb_lower_breakout_with_volume_surge':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Close', 0) < data.iloc[-1].get('BBL_20_2.0', 0) and
                     data.iloc[-2].get('Close', 0) >= data.iloc[-2].get('BBL_20_2.0', 0) and
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.5),
    
    # BB 평균 회귀 + ADX 약세
    'bb_mean_reversion_with_weak_adx':
        lambda data: (len(data) > 1 and 
                     ((data.iloc[-1].get('Close', 0) > data.iloc[-1].get('BBL_20_2.0', 0) and
                       data.iloc[-2].get('Close', 0) <= data.iloc[-2].get('BBL_20_2.0', 0)) or
                      (data.iloc[-1].get('Close', 0) < data.iloc[-1].get('BBU_20_2.0', 0) and
                       data.iloc[-2].get('Close', 0) >= data.iloc[-2].get('BBU_20_2.0', 0))) and
                     data.iloc[-1].get('ADX_14', 0) <= 20),
} 