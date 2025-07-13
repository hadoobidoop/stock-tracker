from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals.signal_weights import SIGNAL_WEIGHTS

logger = get_logger(__name__)


class StochSignalDetector(SignalDetector):
    """스토캐스틱 신호 감지기"""
    
    def __init__(self, weight: float = None):
        weight = weight or SIGNAL_WEIGHTS["stoch_cross"]
        super().__init__(weight, "Stoch_Detector")
        self.required_columns = ['STOCHk_14_3_3', 'STOCHd_14_3_3']
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """스토캐스틱의 크로스, 반전, 상태를 종합적으로 감지합니다."""

        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []

        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]

        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []

        # 조정 계수 가져오기
        adj = self.get_adjustment_factor(market_trend, "momentum_reversal_adj")

        k = latest_data['STOCHk_14_3_3']
        d = latest_data['STOCHd_14_3_3']
        prev_k = prev_data['STOCHk_14_3_3']
        prev_d = prev_data['STOCHd_14_3_3']

        is_golden_cross = prev_k < prev_d and k > d
        is_dead_cross = prev_k > prev_d and k < d

        # --- 매수 신호 로직 ---
        # 신호 1: 골든 크로스 (이벤트)
        if is_golden_cross:
            # 과매도 구간에서 발생 시 더 강한 신호
            if k < 30:
                strength = (30 - k) / 30
                buy_score += self.weight * adj * (1.2 + strength) # 1.2배 가중치 + 강도
                buy_details.append(f"스토캐스틱 과매도 골든크로스 (K:{k:.2f})")
            # 일반 구간
            elif k < 80: # 과매수 직전까지만
                buy_score += self.weight * adj
                buy_details.append(f"스토캐스틱 골든크로스 (K:{k:.2f})")
        # 신호 2: 과매도 상태 (상태)
        elif k < 20:
            strength = (20 - k) / 20
            # 반등 시(K 증가) 점수 추가
            if k > prev_k:
                buy_score += self.weight * adj * (0.5 + strength) # 0.5배 가중치 + 강도
                buy_details.append(f"스토캐스틱 과매도 상태에서 반등 (K:{k:.2f})")
            else:
                buy_score += self.weight * adj * 0.3 # 기본 30% 가중치
                buy_details.append(f"스토캐스틱 과매도 상태 지속 (K:{k:.2f})")


        # --- 매도 신호 로직 ---
        # 신호 1: 데드 크로스 (이벤트)
        if is_dead_cross:
            # 과매수 구간에서 발생 시 더 강한 신호
            if k > 70:
                strength = (k - 70) / 30
                sell_score += self.weight * adj * (1.2 + strength) # 1.2배 가중치 + 강도
                sell_details.append(f"스토캐스틱 과매수 데드크로스 (K:{k:.2f})")
            # 일반 구간
            elif k > 20: # 과매도 직전까지만
                sell_score += self.weight * adj
                sell_details.append(f"스토캐스틱 데드크로스 (K:{k:.2f})")
        # 신호 2: 과매수 상태 (상태)
        elif k > 80:
            strength = (k - 80) / 20
            # 하락 시(K 감소) 점수 추가
            if k < prev_k:
                sell_score += self.weight * adj * (0.5 + strength) # 0.5배 가중치 + 강도
                sell_details.append(f"스토캐스틱 과매수 상태에서 하락 (K:{k:.2f})")
            else:
                sell_score += self.weight * adj * 0.3 # 기본 30% 가중치
                sell_details.append(f"스토캐스틱 과매수 상태 지속 (K:{k:.2f})")

        return buy_score, sell_score, buy_details, sell_details 