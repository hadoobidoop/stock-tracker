from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_WEIGHTS, VOLUME_SURGE_FACTOR

logger = get_logger(__name__)


class MACDVolumeDetector(SignalDetector):
    """MACD + 거래량 확인 복합 신호 감지기"""
    
    def __init__(self, weight: float = None):
        weight = weight or SIGNAL_WEIGHTS["macd_volume_confirm"]
        super().__init__(weight, "MACD_Volume_Detector")
        self.required_columns = ['MACD_12_26_9', 'MACDs_12_26_9', 'Volume', 'Volume_SMA_20']
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """MACD + 거래량 복합 신호를 감지합니다."""
        
        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []
        
        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]
        
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        
        # 조정 계수 가져오기
        volume_adj = self.get_adjustment_factor(market_trend, "volume_adj")
        
        # MACD 골든 크로스 + 거래량 급증
        if (prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and 
            latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']) and \
           (latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR):
            buy_score += self.weight * volume_adj
            buy_details.append(
                f"MACD 골든 크로스 & 거래량 급증 확인 (MACD:{latest_data['MACD_12_26_9']:.2f}, Volume:{latest_data['Volume']:,})")
        
        # MACD 데드 크로스 + 하락 거래량 급증
        if (prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and 
            latest_data['MACD_12_26_9'] < latest_data['MACDs_12_26_9']) and \
           (latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR and 
            latest_data['Close'] < prev_data['Close']):
            sell_score += self.weight * volume_adj
            sell_details.append(
                f"MACD 데드 크로스 & 하락 거래량 급증 확인 (MACD:{latest_data['MACD_12_26_9']:.2f}, Volume:{latest_data['Volume']:,})")
        
        return buy_score, sell_score, buy_details, sell_details