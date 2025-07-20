from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VolumeSignalDetector(SignalDetector):
    """거래량 급증 신호 감지기 - 파라미터 주입 방식 지원"""
    
    def __init__(self, weight: float, name: str = None, parameters: Optional[Dict] = None):
        super().__init__(weight, name or "Volume_Detector")
        self.required_columns = ['Volume', 'Volume_SMA_20']
        
        # 기본 파라미터 설정
        default_params = {
            'volume_surge_factor': 1.5,  # 거래량 급증 임계값
            'max_volume_strength': 1.0,  # 거래량 강도 최대값
            'max_price_strength': 1.0,   # 가격 변화 강도 최대값
            'price_change_limit': 0.01,  # 가격 변화 한계 (1%)
            'trend_continuation_weight': 0.5,  # 추세 지속 가중치
            'min_trend_days': 3,         # 최소 추세 확인 일수
            'volume_weight_multiplier': 100  # 가격 변화율 곱셈 인수
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
    
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
        
        # 거래량 급증 (현재 거래량 > 평균 거래량 * volume_surge_factor)
        volume_ratio = latest_data['Volume'] / latest_data['Volume_SMA_20']
        
        if volume_ratio > self.params['volume_surge_factor']:
            # 거래량 급증 강도 계산 (최대값까지)
            volume_strength = min(
                (volume_ratio - self.params['volume_surge_factor']) / self.params['volume_surge_factor'], 
                self.params['max_volume_strength']
            )
            
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                # 상승폭에 따른 추가 가중치
                price_change_pct = (latest_data['Close'] - prev_data['Close']) / prev_data['Close']
                price_strength = min(
                    price_change_pct * self.params['volume_weight_multiplier'], 
                    self.params['max_price_strength']
                )
                
                buy_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                buy_details.append(
                    f"거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.params['volume_surge_factor']})")
            
            # 하락 시 거래량 급증
            elif latest_data['Close'] < prev_data['Close']:
                # 하락폭에 따른 추가 가중치
                price_change_pct = (prev_data['Close'] - latest_data['Close']) / prev_data['Close']
                price_strength = min(
                    price_change_pct * self.params['volume_weight_multiplier'], 
                    self.params['max_price_strength']
                )
                
                sell_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                sell_details.append(
                    f"하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.params['volume_surge_factor']})")
        
        # 거래량 증가 추세 (설정된 일수만큼 연속 증가)
        elif len(df) >= self.params['min_trend_days'] + 1:
            vol_trend_days = df['Volume'].iloc[-self.params['min_trend_days']:].values
            if all(vol_trend_days[i] > vol_trend_days[i-1] for i in range(1, len(vol_trend_days))):
                # 상승 시 거래량 증가 추세
                if latest_data['Close'] > prev_data['Close']:
                    buy_score += self.weight * volume_adj * self.params['trend_continuation_weight']
                    buy_details.append(f"{self.params['min_trend_days']}일 연속 거래량 증가")
                # 하락 시 거래량 증가 추세
                elif latest_data['Close'] < prev_data['Close']:
                    sell_score += self.weight * volume_adj * self.params['trend_continuation_weight']
                    sell_details.append(f"{self.params['min_trend_days']}일 연속 거래량 증가")
        
        return buy_score, sell_score, buy_details, sell_details 