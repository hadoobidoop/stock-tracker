from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from domain.analysis.config.signals import VOLUME_SURGE_FACTOR

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
        volume_ratio = latest_data['Volume'] / latest_data['Volume_SMA_20']
        
        if volume_ratio > VOLUME_SURGE_FACTOR:
            # 거래량 급증 강도 계산 (최대 2배까지)
            volume_strength = min((volume_ratio - VOLUME_SURGE_FACTOR) / VOLUME_SURGE_FACTOR, 1.0)
            
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                # 상승폭에 따른 추가 가중치
                price_change_pct = (latest_data['Close'] - prev_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 100, 1.0)  # 최대 1% 상승까지
                
                buy_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                buy_details.append(
                    f"거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")
            
            # 하락 시 거래량 급증
            elif latest_data['Close'] < prev_data['Close']:
                # 하락폭에 따른 추가 가중치
                price_change_pct = (prev_data['Close'] - latest_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 100, 1.0)  # 최대 1% 하락까지
                
                sell_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                sell_details.append(
                    f"하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")
        
        # 거래량 증가 추세 (3일 연속 증가)
        elif len(df) >= 4:
            vol_3d = df['Volume'].iloc[-3:].values
            if all(vol_3d[i] > vol_3d[i-1] for i in range(1, len(vol_3d))):
                # 상승 시 거래량 증가 추세
                if latest_data['Close'] > prev_data['Close']:
                    buy_score += self.weight * volume_adj * 0.5  # 50% 가중치
                    buy_details.append("3일 연속 거래량 증가")
                # 하락 시 거래량 증가 추세
                elif latest_data['Close'] < prev_data['Close']:
                    sell_score += self.weight * volume_adj * 0.5  # 50% 가중치
                    sell_details.append("3일 연속 거래량 증가")
        
        return buy_score, sell_score, buy_details, sell_details 