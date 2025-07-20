from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RSISignalDetector(SignalDetector):
    """RSI 과매수/과매도 신호 감지기 - 파라미터 주입 방식 지원"""
    
    def __init__(self, weight: float, name: str = None, parameters: Optional[Dict] = None):
        super().__init__(weight, name or "RSI_Detector")
        self.required_columns = ['RSI_14']
        
        # 기본 파라미터 설정
        default_params = {
            'oversold_threshold': 35,      # 과매도 임계값
            'overbought_threshold': 70,    # 과매수 임계값
            'neutral_lower': 45,           # 중립 하한
            'neutral_upper': 55,           # 중립 상한
            'exit_bonus_multiplier': 1.2,  # 과매수/과매도 탈출 보너스
            'continuation_weight': 0.5,    # 지속 신호 가중치
            'reversal_strength_factor': 1.0  # 반전 강도 계수
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """RSI 과매수/과매도 신호를 감지합니다."""
        
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
        
        current_rsi = latest_data['RSI_14']
        prev_rsi = prev_data['RSI_14']
        
        # RSI 과매도 구간 매수 신호
        if current_rsi <= self.params['oversold_threshold']:
            strength = (self.params['oversold_threshold'] - current_rsi) / self.params['oversold_threshold']
            buy_score += self.weight * momentum_reversal_adj * (1 + strength * self.params['reversal_strength_factor'])
            buy_details.append(f"RSI 과매도 구간 ({current_rsi:.2f})")
        
        # RSI 과매도 탈출 매수 신호
        elif prev_rsi <= self.params['oversold_threshold'] < current_rsi:
            buy_score += self.weight * momentum_reversal_adj * self.params['exit_bonus_multiplier']
            buy_details.append(f"RSI 과매도 탈출 ({prev_rsi:.2f} -> {current_rsi:.2f})")
        
        # RSI 중립선 상향 돌파 (모멘텀 매수)
        elif prev_rsi < self.params['neutral_upper'] < current_rsi:
            buy_score += self.weight * momentum_reversal_adj * 0.8
            buy_details.append(f"RSI 상승 모멘텀 ({prev_rsi:.2f} -> {current_rsi:.2f})")
        
        # RSI 과매수 구간 매도 신호
        if current_rsi >= self.params['overbought_threshold']:
            strength = (current_rsi - self.params['overbought_threshold']) / (100 - self.params['overbought_threshold'])
            sell_score += self.weight * momentum_reversal_adj * (1 + strength * self.params['reversal_strength_factor'])
            sell_details.append(f"RSI 과매수 구간 ({current_rsi:.2f})")
        
        # RSI 과매수 탈출 매도 신호
        elif prev_rsi >= self.params['overbought_threshold'] > current_rsi:
            sell_score += self.weight * momentum_reversal_adj * self.params['exit_bonus_multiplier']
            sell_details.append(f"RSI 과매수 탈출 ({prev_rsi:.2f} -> {current_rsi:.2f})")
        
        # RSI 중립선 하향 돌파 (모멘텀 매도)
        elif prev_rsi > self.params['neutral_lower'] > current_rsi:
            sell_score += self.weight * momentum_reversal_adj * 0.8
            sell_details.append(f"RSI 하락 모멘텀 ({prev_rsi:.2f} -> {current_rsi:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 