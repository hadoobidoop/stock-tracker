from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class SMASignalDetector(SignalDetector):
    """SMA 골든/데드 크로스 신호 감지기"""
    
    def __init__(self, weight: float):
        super().__init__(weight, "SMA_Detector")
        self.required_columns = ['SMA_5', 'SMA_20', 'ADX_14']
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """SMA 크로스 및 추세 지속 신호를 감지합니다."""

        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []

        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]

        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []

        # 조정 계수 가져오기
        trend_follow_buy_adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")
        trend_follow_sell_adj = self.get_adjustment_factor(market_trend, "trend_follow_sell_adj")

        is_golden_cross = prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']
        is_dead_cross = prev_data['SMA_5'] > prev_data['SMA_20'] and latest_data['SMA_5'] < latest_data['SMA_20']
        adx_strength = latest_data['ADX_14']

        # --- 매수 신호 로직 ---
        if is_golden_cross:
            sma_cross_buy_score = self.weight * trend_follow_buy_adj
            detail_msg = "SMA 골든 크로스"
            # ADX 강도에 따른 가중치 조정
            if adx_strength >= 25:
                sma_cross_buy_score *= 1.2
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < 20:
                sma_cross_buy_score *= 0.8
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"
            
            buy_score += sma_cross_buy_score
            buy_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")
        
        # 상승 추세 지속 (크로스 없음)
        elif latest_data['SMA_5'] > latest_data['SMA_20']:
            # ADX가 20 이상일 때만 추세 지속으로 인정
            if adx_strength >= 20:
                continuation_score = self.weight * trend_follow_buy_adj * 0.4  # 40% 가중치
                detail_msg = "SMA 상승 추세 지속"
                if adx_strength >= 25:
                    continuation_score *= 1.2 # 강한 추세에서 가중치 부여
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                buy_score += continuation_score
                buy_details.append(detail_msg)

        # --- 매도 신호 로직 ---
        if is_dead_cross:
            sma_cross_sell_score = self.weight * trend_follow_sell_adj
            detail_msg = "SMA 데드 크로스"
            # ADX 강도에 따른 가중치 조정
            if adx_strength >= 25:
                sma_cross_sell_score *= 1.2
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < 20:
                sma_cross_sell_score *= 0.8
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"

            sell_score += sma_cross_sell_score
            sell_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")

        # 하락 추세 지속 (크로스 없음)
        elif latest_data['SMA_5'] < latest_data['SMA_20']:
            # ADX가 20 이상일 때만 추세 지속으로 인정
            if adx_strength >= 20:
                continuation_score = self.weight * trend_follow_sell_adj * 0.4  # 40% 가중치
                detail_msg = "SMA 하락 추세 지속"
                if adx_strength >= 25:
                    continuation_score *= 1.2 # 강한 추세에서 가중치 부여
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                sell_score += continuation_score
                sell_details.append(detail_msg)

        return buy_score, sell_score, buy_details, sell_details 