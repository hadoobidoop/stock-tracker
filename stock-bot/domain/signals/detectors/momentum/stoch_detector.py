from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StochSignalDetector(SignalDetector):
    """스토캐스틱 신호 감지기 - 파라미터 주입 방식 지원"""
    
    def __init__(self, weight: float, name: str = None, parameters: Optional[Dict] = None):
        super().__init__(weight, name or "Stoch_Detector")
        self.required_columns = ['STOCHk_14_3_3', 'STOCHd_14_3_3']
        
        # 기본 파라미터 설정
        default_params = {
            'oversold_threshold_weak': 30,    # 약한 과매도 임계값
            'oversold_threshold_strong': 20,  # 강한 과매도 임계값
            'overbought_threshold_weak': 70,  # 약한 과매수 임계값
            'overbought_threshold_strong': 80, # 강한 과매수 임계값
            'cross_multiplier': 1.2,          # 크로스 신호 가중치
            'reversal_multiplier': 0.5,       # 반전 신호 가중치
            'continuation_multiplier': 0.3,   # 지속 신호 가중치
            'strength_factor': 1.0,           # 강도 계산 계수
            'require_reversal_momentum': True  # 반전 모멘텀 필요 여부
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
    
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
            if k < self.params['oversold_threshold_weak']:
                strength = (self.params['oversold_threshold_weak'] - k) / self.params['oversold_threshold_weak']
                multiplier = self.params['cross_multiplier'] + (strength * self.params['strength_factor'])
                buy_score += self.weight * adj * multiplier
                buy_details.append(f"스토캐스틱 과매도 골든크로스 (K:{k:.2f})")
            # 일반 구간
            elif k < self.params['overbought_threshold_strong']: # 과매수 직전까지만
                buy_score += self.weight * adj
                buy_details.append(f"스토캐스틱 골든크로스 (K:{k:.2f})")
        # 신호 2: 과매도 상태 (상태)
        elif k < self.params['oversold_threshold_strong']:
            strength = (self.params['oversold_threshold_strong'] - k) / self.params['oversold_threshold_strong']
            # 반전 시(K 증가) 점수 추가
            momentum_check = not self.params['require_reversal_momentum'] or k > prev_k
            if momentum_check:
                multiplier = self.params['reversal_multiplier'] + (strength * self.params['strength_factor'])
                buy_score += self.weight * adj * multiplier
                buy_details.append(f"스토캐스틱 과매도 상태에서 반등 (K:{k:.2f})")
            else:
                buy_score += self.weight * adj * self.params['continuation_multiplier']
                buy_details.append(f"스토캐스틱 과매도 상태 지속 (K:{k:.2f})")


        # --- 매도 신호 로직 ---
        # 신호 1: 데드 크로스 (이벤트)
        if is_dead_cross:
            # 과매수 구간에서 발생 시 더 강한 신호
            if k > self.params['overbought_threshold_weak']:
                strength = (k - self.params['overbought_threshold_weak']) / (100 - self.params['overbought_threshold_weak'])
                multiplier = self.params['cross_multiplier'] + (strength * self.params['strength_factor'])
                sell_score += self.weight * adj * multiplier
                sell_details.append(f"스토캐스틱 과매수 데드크로스 (K:{k:.2f})")
            # 일반 구간
            elif k > self.params['oversold_threshold_strong']: # 과매도 직전까지만
                sell_score += self.weight * adj
                sell_details.append(f"스토캐스틱 데드크로스 (K:{k:.2f})")
        # 신호 2: 과매수 상태 (상태)
        elif k > self.params['overbought_threshold_strong']:
            strength = (k - self.params['overbought_threshold_strong']) / (100 - self.params['overbought_threshold_strong'])
            # 하락 시(K 감소) 점수 추가
            momentum_check = not self.params['require_reversal_momentum'] or k < prev_k
            if momentum_check:
                multiplier = self.params['reversal_multiplier'] + (strength * self.params['strength_factor'])
                sell_score += self.weight * adj * multiplier
                sell_details.append(f"스토캐스틱 과매수 상태에서 하락 (K:{k:.2f})")
            else:
                sell_score += self.weight * adj * self.params['continuation_multiplier']
                sell_details.append(f"스토캐스틱 과매수 상태 지속 (K:{k:.2f})")

        return buy_score, sell_score, buy_details, sell_details 