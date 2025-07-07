from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals import SIGNAL_WEIGHTS

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
        """RSI + 스토캐스틱 복합 신호를 감지합니다."""
        
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
        
        # RSI 과매도 탈출 + 스토캐스틱 매수 (과매도 구간에서 골든 크로스)
        if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) and \
           (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3'] and
            latest_data['STOCHk_14_3_3'] < 20):
            buy_score += self.weight * momentum_reversal_adj
            buy_details.append(
                f"RSI/Stoch 동시 매수 신호 (RSI:{latest_data['RSI_14']:.2f}, Stoch %K:{latest_data['STOCHk_14_3_3']:.2f})")
        
        # RSI 과매수 하락 + 스토캐스틱 매도 (과매수 구간에서 데드 크로스)
        if (prev_data['RSI_14'] >= 70 > latest_data['RSI_14']) and \
           (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHk_14_3_3'] < latest_data['STOCHd_14_3_3'] and
            latest_data['STOCHk_14_3_3'] > 80):
            sell_score += self.weight * momentum_reversal_adj
            sell_details.append(
                f"RSI/Stoch 동시 매도 신호 (RSI:{latest_data['RSI_14']:.2f}, Stoch %K:{latest_data['STOCHk_14_3_3']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details