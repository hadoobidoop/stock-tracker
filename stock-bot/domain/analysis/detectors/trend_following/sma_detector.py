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
        """SMA 크로스 신호를 감지합니다."""
        
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
        
        # 골든 크로스 (5일 SMA > 20일 SMA)
        if prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']:
            sma_cross_buy_score = self.weight * trend_follow_buy_adj
            
            # ADX 약세 시 가중치 감소
            if latest_data['ADX_14'] < 25:
                sma_cross_buy_score *= 0.5
                buy_details.append(f"골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
            
            buy_score += sma_cross_buy_score
            buy_details.append(f"골든 크로스 (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")
        
        # 데드 크로스 (5일 SMA < 20일 SMA)
        if prev_data['SMA_5'] > prev_data['SMA_20'] and latest_data['SMA_5'] < latest_data['SMA_20']:
            sma_cross_sell_score = self.weight * trend_follow_sell_adj
            
            # ADX 약세 시 가중치 감소
            if latest_data['ADX_14'] < 25:
                sma_cross_sell_score *= 0.5
                sell_details.append(f"데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
            
            sell_score += sma_cross_sell_score
            sell_details.append(f"데드 크로스 (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 