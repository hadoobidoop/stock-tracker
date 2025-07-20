"""
Volume Rules Module

거래량 관련 규칙 함수들을 정의합니다.
analysis/volume.py의 함수들을 활용하여 규칙을 만듭니다.
"""

from ..analysis.volume import (
    analyze_macd_with_volume,
    get_volume_pattern,
    calculate_volume_strength,
    analyze_volume_price_relationship,
    MacdVolumeEvidence,
    VolumePattern
)

# 거래량 관련 규칙들
VOLUME_RULES = {
    # MACD 골든크로스 + 거래량 급증
    'macd_golden_cross_with_volume_surge':
        lambda data: analyze_macd_with_volume(data)[0] == MacdVolumeEvidence.BULLISH_CROSS_WITH_VOLUME_SURGE,
    
    # MACD 상승 추세 + 거래량 확인
    'macd_bullish_trend_with_volume_confirm':
        lambda data: analyze_macd_with_volume(data)[0] == MacdVolumeEvidence.BULLISH_TREND_WITH_VOLUME_CONFIRM,
    
    # MACD 데드크로스 + 거래량 급증
    'macd_dead_cross_with_volume_surge':
        lambda data: analyze_macd_with_volume(data)[0] == MacdVolumeEvidence.BEARISH_CROSS_WITH_VOLUME_SURGE,
    
    # MACD 하락 추세 + 거래량 확인
    'macd_bearish_trend_with_volume_confirm':
        lambda data: analyze_macd_with_volume(data)[0] == MacdVolumeEvidence.BEARISH_TREND_WITH_VOLUME_CONFIRM,
    
    # 약한 신호
    'macd_volume_weak_signal':
        lambda data: analyze_macd_with_volume(data)[0] == MacdVolumeEvidence.WEAK_SIGNAL,
    
    # 거래량 급증 패턴
    'volume_surge_pattern':
        lambda data: get_volume_pattern(data) == VolumePattern.SURGE,
    
    # 거래량 평균 이상 패턴
    'volume_above_average_pattern':
        lambda data: get_volume_pattern(data) == VolumePattern.ABOVE_AVERAGE,
    
    # 거래량 평균 이하 패턴
    'volume_below_average_pattern':
        lambda data: get_volume_pattern(data) == VolumePattern.BELOW_AVERAGE,
    
    # 거래량 감소 패턴
    'volume_declining_pattern':
        lambda data: get_volume_pattern(data) == VolumePattern.DECLINING,
    
    # 거래량 중립 패턴
    'volume_neutral_pattern':
        lambda data: get_volume_pattern(data) == VolumePattern.NEUTRAL,
    
    # 거래량 강도 높음
    'volume_strength_high':
        lambda data: calculate_volume_strength(data) > 1.5,
    
    # 거래량 강도 보통
    'volume_strength_moderate':
        lambda data: 0.5 < calculate_volume_strength(data) <= 1.5,
    
    # 거래량 강도 낮음
    'volume_strength_low':
        lambda data: calculate_volume_strength(data) <= 0.5,
    
    # 거래량-가격 상관관계 높음
    'volume_price_correlation_high':
        lambda data: analyze_volume_price_relationship(data)['correlation'] > 0.7,
    
    # 거래량-가격 상관관계 보통
    'volume_price_correlation_moderate':
        lambda data: 0.3 < analyze_volume_price_relationship(data)['correlation'] <= 0.7,
    
    # 거래량-가격 상관관계 낮음
    'volume_price_correlation_low':
        lambda data: analyze_volume_price_relationship(data)['correlation'] <= 0.3,
    
    # 거래량-가격 다이버전스 높음
    'volume_price_divergence_high':
        lambda data: analyze_volume_price_relationship(data)['divergence_score'] > 0.7,
    
    # 거래량-가격 다이버전스 보통
    'volume_price_divergence_moderate':
        lambda data: 0.3 < analyze_volume_price_relationship(data)['divergence_score'] <= 0.7,
    
    # 거래량-가격 다이버전스 낮음
    'volume_price_divergence_low':
        lambda data: analyze_volume_price_relationship(data)['divergence_score'] <= 0.3,
    
    # 거래량 급증 (1.5배 이상)
    'volume_surge_1_5x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.5),
    
    # 거래량 급증 (2배 이상)
    'volume_surge_2x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 2.0),
    
    # 거래량 급증 (3배 이상)
    'volume_surge_3x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 3.0),
    
    # 거래량 평균 이상 (1.1배 이상)
    'volume_above_average_1_1x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.1),
    
    # 거래량 평균 이하 (0.8배 이하)
    'volume_below_average_0_8x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) < data.iloc[-1].get('Volume_SMA_20', 0) * 0.8),
    
    # 거래량 평균 이하 (0.5배 이하)
    'volume_below_average_0_5x':
        lambda data: (len(data) > 0 and 
                     data.iloc[-1].get('Volume', 0) < data.iloc[-1].get('Volume_SMA_20', 0) * 0.5),
    
    # 거래량 증가 추세 (3일 연속)
    'volume_increasing_trend_3d':
        lambda data: (len(data) > 3 and 
                     all(data.iloc[-i].get('Volume', 0) > data.iloc[-i-1].get('Volume', 0) 
                         for i in range(1, 4))),
    
    # 거래량 감소 추세 (3일 연속)
    'volume_decreasing_trend_3d':
        lambda data: (len(data) > 3 and 
                     all(data.iloc[-i].get('Volume', 0) < data.iloc[-i-1].get('Volume', 0) 
                         for i in range(1, 4))),
    
    # 거래량 급증 + 가격 상승
    'volume_surge_with_price_rise':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.5 and
                     data.iloc[-1].get('Close', 0) > data.iloc[-2].get('Close', 0)),
    
    # 거래량 급증 + 가격 하락
    'volume_surge_with_price_fall':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Volume', 0) > data.iloc[-1].get('Volume_SMA_20', 0) * 1.5 and
                     data.iloc[-1].get('Close', 0) < data.iloc[-2].get('Close', 0)),
    
    # 거래량 감소 + 가격 상승 (다이버전스)
    'volume_decline_with_price_rise':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Volume', 0) < data.iloc[-1].get('Volume_SMA_20', 0) * 0.8 and
                     data.iloc[-1].get('Close', 0) > data.iloc[-2].get('Close', 0)),
    
    # 거래량 감소 + 가격 하락 (다이버전스)
    'volume_decline_with_price_fall':
        lambda data: (len(data) > 1 and 
                     data.iloc[-1].get('Volume', 0) < data.iloc[-1].get('Volume_SMA_20', 0) * 0.8 and
                     data.iloc[-1].get('Close', 0) < data.iloc[-2].get('Close', 0)),
} 