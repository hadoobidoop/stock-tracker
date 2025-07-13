from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signal_weights import SIGNAL_WEIGHTS

logger = get_logger(__name__)


class RSIStochDetector(SignalDetector):
    """RSI + 스토캐스틱 복합 신호 감지기"""
    
    def __init__(self, weight: float = None):
        weight = weight or SIGNAL_WEIGHTS["rsi_stoch_confirm"]
        super().__init__(weight, "RSI_Stoch_Detector")
        self.required_columns = ['RSI_14', 'STOCHk_14_3_3', 'STOCHd_14_3_3']
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """RSI와 스토캐스틱의 상태와 이벤트를 종합하여 신호를 감지합니다."""

        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []

        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]

        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []

        # 조정 계수 가져오기
        momentum_reversal_adj = self.get_adjustment_factor(market_trend, "momentum_reversal_adj")

        # --- 매수 신호 분석 (과매도 구간) ---
        rsi_val = latest_data['RSI_14']
        stoch_k = latest_data['STOCHk_14_3_3']
        stoch_d = latest_data['STOCHd_14_3_3']

        # 상태 체크: 과매도 구간에 있는가?
        is_rsi_oversold = rsi_val < 30
        is_stoch_oversold = stoch_k < 20

        # 이벤트 체크: 과매도 탈출 또는 골든 크로스 발생
        is_rsi_exiting_oversold = prev_data['RSI_14'] <= 30 < rsi_val
        is_stoch_golden_cross = prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and stoch_k > stoch_d

        base_buy_score = 0.0
        # 신호 1: RSI 과매도 탈출 (강한 신호)
        if is_rsi_exiting_oversold:
            base_buy_score += self.weight * 0.6
            buy_details.append(f"RSI 과매도 탈출 ({prev_data['RSI_14']:.2f} -> {rsi_val:.2f})")
            # 확인 사살: 스토캐스틱 골든크로스 동시 발생
            if is_stoch_golden_cross and is_stoch_oversold:
                base_buy_score += self.weight * 0.4 # 보너스 점수
                buy_details.append("스토캐스틱 골든크로스 확인")

        # 신호 2: RSI 과매도 상태 지속 (약한 신호)
        elif is_rsi_oversold:
            base_buy_score += self.weight * 0.3
            buy_details.append(f"RSI 과매도 상태 지속 ({rsi_val:.2f})")
            # 확인 사살: 스토캐스틱도 과매도 상태
            if is_stoch_oversold:
                base_buy_score += self.weight * 0.2
                buy_details.append(f"스토캐스틱 과매도 상태 지속 (K:{stoch_k:.2f})")

        if base_buy_score > 0:
            buy_score = base_buy_score * momentum_reversal_adj

        # --- 매도 신호 분석 (과매수 구간) ---
        # 상태 체크: 과매수 구간에 있는가?
        is_rsi_overbought = rsi_val > 70
        is_stoch_overbought = stoch_k > 80

        # 이벤트 체크: 과매수 탈출 또는 데드 크로스 발생
        is_rsi_exiting_overbought = prev_data['RSI_14'] >= 70 > rsi_val
        is_stoch_dead_cross = prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and stoch_k < stoch_d
        
        base_sell_score = 0.0
        # 신호 1: RSI 과매수 탈출 (강한 신호)
        if is_rsi_exiting_overbought:
            base_sell_score += self.weight * 0.6
            sell_details.append(f"RSI 과매수 탈출 ({prev_data['RSI_14']:.2f} -> {rsi_val:.2f})")
            # 확인 사살: 스토캐스틱 데드크로스 동시 발생
            if is_stoch_dead_cross and is_stoch_overbought:
                base_sell_score += self.weight * 0.4 # 보너스 점수
                sell_details.append("스토캐스틱 데드크로스 확인")

        # 신호 2: RSI 과매수 상태 지속 (약한 신호)
        elif is_rsi_overbought:
            base_sell_score += self.weight * 0.3
            sell_details.append(f"RSI 과매수 상태 지속 ({rsi_val:.2f})")
            # 확인 사살: 스토캐스틱도 과매수 상태
            if is_stoch_overbought:
                base_sell_score += self.weight * 0.2
                sell_details.append(f"스토캐스틱 과매수 상태 지속 (K:{stoch_k:.2f})")

        if base_sell_score > 0:
            sell_score = base_sell_score * momentum_reversal_adj

        return buy_score, sell_score, buy_details, sell_details