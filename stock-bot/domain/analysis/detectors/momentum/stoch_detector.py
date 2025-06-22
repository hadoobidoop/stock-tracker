from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_WEIGHTS

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
        """스토캐스틱 크로스 신호를 감지합니다."""
        
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
        
        # 매수 신호 1: %K가 %D를 상향 돌파
        if (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and
                latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3']):
            # 과매도 구간에서 더 강한 신호
            if latest_data['STOCHk_14_3_3'] < 30:
                strength = (30 - latest_data['STOCHk_14_3_3']) / 30  # 낮을수록 강한 신호
                buy_score += self.weight * momentum_reversal_adj * (1 + strength)
                buy_details.append(f"스토캐스틱 과매도 상향돌파 (%K:{latest_data['STOCHk_14_3_3']:.2f} > %D:{latest_data['STOCHd_14_3_3']:.2f})")
            # 일반 구간에서는 기본 신호
            elif latest_data['STOCHk_14_3_3'] < 85:  # 85로 완화
                buy_score += self.weight * momentum_reversal_adj
                buy_details.append(f"스토캐스틱 매수 (%K:{latest_data['STOCHk_14_3_3']:.2f} > %D:{latest_data['STOCHd_14_3_3']:.2f})")
        
        # 매수 신호 2: 과매도 구간에서 반등
        elif latest_data['STOCHk_14_3_3'] < 20 and latest_data['STOCHk_14_3_3'] > prev_data['STOCHk_14_3_3']:
            strength = (20 - latest_data['STOCHk_14_3_3']) / 20
            buy_score += self.weight * momentum_reversal_adj * strength
            buy_details.append(f"스토캐스틱 과매도 반등 (%K:{prev_data['STOCHk_14_3_3']:.2f} -> {latest_data['STOCHk_14_3_3']:.2f})")
        
        # 매도 신호 1: %K가 %D를 하향 돌파
        if (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and
                latest_data['STOCHk_14_3_3'] < latest_data['STOCHd_14_3_3']):
            # 과매수 구간에서 더 강한 신호
            if latest_data['STOCHk_14_3_3'] > 70:
                strength = (latest_data['STOCHk_14_3_3'] - 70) / 30  # 높을수록 강한 신호
                sell_score += self.weight * momentum_reversal_adj * (1 + strength)
                sell_details.append(f"스토캐스틱 과매수 하향돌파 (%K:{latest_data['STOCHk_14_3_3']:.2f} < %D:{latest_data['STOCHd_14_3_3']:.2f})")
            # 일반 구간에서는 기본 신호
            elif latest_data['STOCHk_14_3_3'] > 15:  # 15로 완화
                sell_score += self.weight * momentum_reversal_adj
                sell_details.append(f"스토캐스틱 매도 (%K:{latest_data['STOCHk_14_3_3']:.2f} < %D:{latest_data['STOCHd_14_3_3']:.2f})")
        
        # 매도 신호 2: 과매수 구간에서 하락
        elif latest_data['STOCHk_14_3_3'] > 80 and latest_data['STOCHk_14_3_3'] < prev_data['STOCHk_14_3_3']:
            strength = (latest_data['STOCHk_14_3_3'] - 80) / 20
            sell_score += self.weight * momentum_reversal_adj * strength
            sell_details.append(f"스토캐스틱 과매수 하락 (%K:{prev_data['STOCHk_14_3_3']:.2f} -> {latest_data['STOCHk_14_3_3']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 