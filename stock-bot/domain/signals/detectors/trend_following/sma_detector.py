from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class SMASignalDetector(SignalDetector):
    """SMA 골든/데드 크로스 신호 감지기 - 파라미터 주입 방식 지원"""
    
    def __init__(self, weight: float, name: str = None, parameters: Optional[Dict] = None):
        super().__init__(weight, name or "SMA_Detector")
        self.required_columns = ['SMA_5', 'SMA_20', 'ADX_14']
        
        # 기본 파라미터 설정
        default_params = {
            'adx_threshold': 20,
            'adx_strong_threshold': 25,
            'continuation_weight': 0.4,
            'trend_confirmation_required': True,
            'strong_trend_multiplier': 1.2,
            'weak_trend_multiplier': 0.8
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
    
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
            if adx_strength >= self.params['adx_strong_threshold']:
                sma_cross_buy_score *= self.params['strong_trend_multiplier']
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < self.params['adx_threshold']:
                sma_cross_buy_score *= self.params['weak_trend_multiplier']
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"
            
            buy_score += sma_cross_buy_score
            buy_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")
        
        # 상승 추세 지속 (크로스 없음)
        elif latest_data['SMA_5'] > latest_data['SMA_20']:
            # 파라미터에 따른 추세 확인 필요 여부 체크
            trend_check = not self.params['trend_confirmation_required'] or adx_strength >= self.params['adx_threshold']
            if trend_check:
                continuation_score = self.weight * trend_follow_buy_adj * self.params['continuation_weight']
                detail_msg = "SMA 상승 추세 지속"
                if adx_strength >= self.params['adx_strong_threshold']:
                    continuation_score *= self.params['strong_trend_multiplier']
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                buy_score += continuation_score
                buy_details.append(detail_msg)

        # --- 매도 신호 로직 ---
        if is_dead_cross:
            sma_cross_sell_score = self.weight * trend_follow_sell_adj
            detail_msg = "SMA 데드 크로스"
            # ADX 강도에 따른 가중치 조정
            if adx_strength >= self.params['adx_strong_threshold']:
                sma_cross_sell_score *= self.params['strong_trend_multiplier']
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < self.params['adx_threshold']:
                sma_cross_sell_score *= self.params['weak_trend_multiplier']
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"

            sell_score += sma_cross_sell_score
            sell_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")

        # 하락 추세 지속 (크로스 없음)
        elif latest_data['SMA_5'] < latest_data['SMA_20']:
            # 파라미터에 따른 추세 확인 필요 여부 체크
            trend_check = not self.params['trend_confirmation_required'] or adx_strength >= self.params['adx_threshold']
            if trend_check:
                continuation_score = self.weight * trend_follow_sell_adj * self.params['continuation_weight']
                detail_msg = "SMA 하락 추세 지속"
                if adx_strength >= self.params['adx_strong_threshold']:
                    continuation_score *= self.params['strong_trend_multiplier']
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                sell_score += continuation_score
                sell_details.append(detail_msg)

        return buy_score, sell_score, buy_details, sell_details 