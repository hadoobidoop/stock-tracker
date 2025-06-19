from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.analysis_settings import VOLUME_SURGE_FACTOR

logger = get_logger(__name__)


class VolumeSignalDetector(SignalDetector):
    """거래량 급증 신호 감지기"""
    
    def __init__(self, weight: float):
        super().__init__(weight, "Volume_Detector")
        self.required_columns = ['Volume', 'Volume_SMA_20']
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """거래량 급증 신호를 감지합니다."""
        
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
        
        # 거래량 급증 (현재 거래량 > 평균 거래량 * VOLUME_SURGE_FACTOR)
        if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                buy_score += self.weight * volume_adj
                buy_details.append(
                    f"거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")
            
            # 하락 시 거래량 급증
            elif latest_data['Close'] < prev_data['Close']:
                sell_score += self.weight * volume_adj
                sell_details.append(
                    f"하락 시 거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")
        
        return buy_score, sell_score, buy_details, sell_details 