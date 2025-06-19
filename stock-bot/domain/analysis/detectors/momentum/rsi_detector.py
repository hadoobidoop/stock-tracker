from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class RSISignalDetector(SignalDetector):
    """RSI 과매수/과매도 신호 감지기"""
    
    def __init__(self, weight: float):
        super().__init__(weight, "RSI_Detector")
        self.required_columns = ['RSI_14']
    
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
        
        # RSI 과매도 탈출 (RSI <= 30 -> RSI > 30)
        if prev_data['RSI_14'] <= 30 < latest_data['RSI_14']:
            buy_score += self.weight * momentum_reversal_adj
            buy_details.append(f"RSI 과매도 탈출 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")
        
        # RSI 과매수 하락 (RSI >= 70 -> RSI < 70)
        if prev_data['RSI_14'] >= 70 > latest_data['RSI_14']:
            sell_score += self.weight * momentum_reversal_adj
            sell_details.append(f"RSI 과매수 하락 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 