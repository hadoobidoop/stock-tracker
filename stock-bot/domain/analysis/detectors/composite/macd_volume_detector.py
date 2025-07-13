from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signal_weights import SIGNAL_WEIGHTS
from domain.analysis.config.realtime_signal_settings import VOLUME_SURGE_FACTOR

logger = get_logger(__name__)


class MACDVolumeDetector(SignalDetector):
    """MACD + 거래량 확인 복합 신호 감지기"""
    
    def __init__(self, weight: float = None):
        weight = weight or SIGNAL_WEIGHTS["macd_volume_confirm"]
        super().__init__(weight, "MACD_Volume_Detector")
        self.required_columns = ['MACD_12_26_9', 'MACDs_12_26_9', 'Volume', 'Volume_SMA_20']
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """MACD와 거래량의 상태와 이벤트를 유연하게 조합하여 신호를 감지합니다."""

        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        buy_score, sell_score = 0.0, 0.0
        buy_details, sell_details = [], []

        adj = self.get_adjustment_factor(market_trend, "volume_adj")

        # --- MACD 상태 및 이벤트 정의 ---
        is_golden_cross = prev['MACD_12_26_9'] < prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] > latest['MACDs_12_26_9']
        is_dead_cross = prev['MACD_12_26_9'] > prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] < latest['MACDs_12_26_9']
        is_bullish_state = latest['MACD_12_26_9'] > latest['MACDs_12_26_9']
        is_bearish_state = latest['MACD_12_26_9'] < latest['MACDs_12_26_9']

        # --- 거래량 상태 및 이벤트 정의 ---
        is_volume_surge = latest['Volume'] > latest['Volume_SMA_20'] * VOLUME_SURGE_FACTOR
        is_volume_above_avg = latest['Volume'] > latest['Volume_SMA_20']

        # --- 매수 신호 조합 ---
        macd_buy_signal_strength = 0.0
        if is_golden_cross:
            macd_buy_signal_strength = 1.0  # 이벤트
            buy_details.append("MACD 골든 크로스")
        elif is_bullish_state:
            macd_buy_signal_strength = 0.5  # 상태
            buy_details.append("MACD 상승 추세 지속")

        if macd_buy_signal_strength > 0:
            volume_confirmation_strength = 0.0
            if is_volume_surge:
                volume_confirmation_strength = 1.0 # 이벤트
                buy_details.append("거래량 급증 확인")
            elif is_volume_above_avg:
                volume_confirmation_strength = 0.5 # 상태
                buy_details.append("평균 이상 거래량 확인")

            if volume_confirmation_strength > 0:
                final_buy_strength = macd_buy_signal_strength * volume_confirmation_strength
                buy_score += self.weight * adj * final_buy_strength

        # --- 매도 신호 조합 ---
        macd_sell_signal_strength = 0.0
        if is_dead_cross:
            macd_sell_signal_strength = 1.0 # 이벤트
            sell_details.append("MACD 데드 크로스")
        elif is_bearish_state:
            macd_sell_signal_strength = 0.5 # 상태
            sell_details.append("MACD 하락 추세 지속")

        if macd_sell_signal_strength > 0:
            volume_confirmation_strength = 0.0
            # 하락 시에는 거래량 급증만 확인 (더 보수적인 조건)
            if is_volume_surge and latest['Close'] < prev['Close']:
                volume_confirmation_strength = 1.0
                sell_details.append("하락 거래량 급증 확인")
            elif is_volume_above_avg and latest['Close'] < prev['Close']:
                volume_confirmation_strength = 0.5
                sell_details.append("하락 시 평균 이상 거래량 확인")

            if volume_confirmation_strength > 0:
                final_sell_strength = macd_sell_signal_strength * volume_confirmation_strength
                sell_score += self.weight * adj * final_sell_strength

        return buy_score, sell_score, buy_details, sell_details