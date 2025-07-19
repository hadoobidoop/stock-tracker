"""
시장 추세별 신호 조정 계수 설정
- BULLISH/BEARISH/NEUTRAL별 신호 가중치 조정
"""

SIGNAL_ADJUSTMENT_FACTORS_BY_TREND = {
    "BULLISH": {
        "trend_follow_buy_adj": 1.2,    # 상승 추세에서 매수 신호 강화
        "trend_follow_sell_adj": 0.5,   # 상승 추세에서 매도 신호 약화
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.2,              # 불리시장에서 거래량은 더 긍정적
        "bb_kc_adj": 1.2,               # 불리시장에서 확장도 더 긍정적
        "pivot_fib_adj": 1.3
    },
    "BEARISH": {
        "trend_follow_buy_adj": 0.5,    # 하락 추세에서 매수 신호 약화
        "trend_follow_sell_adj": 1.2,   # 하락 추세에서 매도 신호 강화
        "momentum_reversal_adj": 0.8,
        "volume_adj": 1.2,              # 베어리시장에서 거래량은 하락 확인
        "bb_kc_adj": 1.2,               # 베어리시장에서 확장도 하락 확인
        "pivot_fib_adj": 0.8
    },
    "NEUTRAL": {
        "trend_follow_buy_adj": 0.3,    # 중립장에서 추세 추종 신호 더 약화
        "trend_follow_sell_adj": 0.3,   # 중립장에서 추세 추종 신호 더 약화
        "momentum_reversal_adj": 1.5,   # 중립장에서 반전 신호 가중치 더 높임
        "volume_adj": 1.0,              # 중립장에서 거래량 중립적
        "bb_kc_adj": 1.5,               # 중립장에서 변동성 확장은 더 중요
        "pivot_fib_adj": 1.8            # 중립장에서 지지/저항 신호 중요도 더 높임
    }
} 