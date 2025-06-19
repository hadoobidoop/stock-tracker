from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class MACDSignalDetector(SignalDetector):
    """MACD 골든/데드 크로스 신호 감지기"""
    
    def __init__(self, weight: float):
        super().__init__(weight, "MACD_Detector")
        self.required_columns = ['MACD_12_26_9', 'MACDs_12_26_9', 'ADX_14']
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """MACD 크로스 신호를 감지합니다."""
        
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
        
        # 골든 크로스 (MACD > Signal)
        if prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']:
            macd_cross_buy_score = self.weight * trend_follow_buy_adj
            
            # ADX 약세 시 가중치 감소
            if latest_data['ADX_14'] < 25:
                macd_cross_buy_score *= 0.5
                buy_details.append(f"MACD 골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
            
            buy_score += macd_cross_buy_score
            buy_details.append(f"MACD 골든 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} > Signal:{latest_data['MACDs_12_26_9']:.2f})")
        
        # 데드 크로스 (MACD < Signal)
        if prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] < latest_data['MACDs_12_26_9']:
            macd_cross_sell_score = self.weight * trend_follow_sell_adj
            
            # ADX 약세 시 가중치 감소
            if latest_data['ADX_14'] < 25:
                macd_cross_sell_score *= 0.5
                sell_details.append(f"MACD 데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
            
            sell_score += macd_cross_sell_score
            sell_details.append(f"MACD 데드 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} < Signal:{latest_data['MACDs_12_26_9']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 