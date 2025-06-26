from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals import SIGNAL_WEIGHTS

logger = get_logger(__name__)


class ADXSignalDetector(SignalDetector):
    """ADX 강한 추세 신호 감지기"""
    
    def __init__(self, weight: float = None):
        weight = weight or SIGNAL_WEIGHTS["adx_strong_trend"]
        super().__init__(weight, "ADX_Detector")
        self.required_columns = ['ADX_14', 'DMP_14', 'DMN_14']
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """ADX 강한 추세 신호를 감지합니다."""
        
        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []
        
        latest_data = df.iloc[-1]
        
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        
        # 조정 계수 가져오기
        trend_follow_buy_adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")
        trend_follow_sell_adj = self.get_adjustment_factor(market_trend, "trend_follow_sell_adj")
        
        # ADX > 25일 때만 강한 추세로 간주
        if latest_data['ADX_14'] > 25:
            # +DI > -DI: 강한 상승 추세
            if latest_data.get('DMP_14', 0) > latest_data.get('DMN_14', 0):
                buy_score += self.weight * trend_follow_buy_adj
                buy_details.append(f"ADX 강한 상승 추세 ({latest_data['ADX_14']:.2f})")
            
            # -DI > +DI: 강한 하락 추세
            elif latest_data.get('DMN_14', 0) > latest_data.get('DMP_14', 0):
                sell_score += self.weight * trend_follow_sell_adj
                sell_details.append(f"ADX 강한 하락 추세 ({latest_data['ADX_14']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 