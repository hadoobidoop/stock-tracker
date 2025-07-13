from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
from domain.analysis.models.trading_signal import TechnicalIndicatorEvidence

logger = get_logger(__name__)


class BalancedVolumeDetector(VolumeSignalDetector):
    """균형 전략용 거래량 신호 감지기 - 안정적인 신호 감지"""
    
    def __init__(self, weight: float):
        super().__init__(weight)
        self.name = "Balanced_Volume_Detector"
        # Balanced 전략은 안정적인 설정 사용
        self.volume_surge_threshold = 1.5  # 기본값 유지
        self.volume_trend_days = 3  # 기본값 유지
        self.volume_confirmation_required = True  # 거래량 확인 필수
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """균형잡힌 거래량 신호를 감지합니다."""
        
        # 근거 수집 초기화
        self.technical_evidences = []
        
        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []
        
        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]
        
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        
        # 조정 계수 가져오기 (Balanced는 안정적인 조정)
        volume_adj = self.get_adjustment_factor(market_trend, "volume_adj")
        
        # 거래량 급증 (표준 임계값 사용)
        volume_ratio = latest_data['Volume'] / latest_data['Volume_SMA_20']
        
        if volume_ratio > self.volume_surge_threshold:
            # 거래량 급증 강도 계산 (안정적인 범위)
            volume_strength = min((volume_ratio - self.volume_surge_threshold) / self.volume_surge_threshold, 1.0)
            
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                # 상승폭에 따른 추가 가중치 (안정적인 범위)
                price_change_pct = (latest_data['Close'] - prev_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 100, 1.0)  # 최대 1% 상승까지
                
                buy_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                buy_details.append(
                    f"Balanced 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                           volume_ratio, f"Balanced 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})",
                                           self.weight * volume_adj * (1 + volume_strength + price_strength))
                )
            
            # 하락 시 거래량 급증
            elif latest_data['Close'] < prev_data['Close']:
                # 하락폭에 따른 추가 가중치 (안정적인 범위)
                price_change_pct = (prev_data['Close'] - latest_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 100, 1.0)  # 최대 1% 하락까지
                
                sell_score += self.weight * volume_adj * (1 + volume_strength + price_strength)
                sell_details.append(
                    f"Balanced 하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                           volume_ratio, f"Balanced 하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})",
                                           self.weight * volume_adj * (1 + volume_strength + price_strength))
                )
        
        # 거래량 증가 추세 (표준 기간 사용)
        elif len(df) >= 4:
            vol_3d = df['Volume'].iloc[-3:].values
            if all(vol_3d[i] > vol_3d[i-1] for i in range(1, len(vol_3d))):
                # 상승 시 거래량 증가 추세
                if latest_data['Close'] > prev_data['Close']:
                    buy_score += self.weight * volume_adj * 0.5  # 50% 가중치 (표준)
                    buy_details.append("Balanced 3일 연속 거래량 증가")
                    
                    # 근거 수집
                    self.technical_evidences.append(
                        self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                               volume_ratio, "Balanced 3일 연속 거래량 증가",
                                               self.weight * volume_adj * 0.5)
                    )
                # 하락 시 거래량 증가 추세
                elif latest_data['Close'] < prev_data['Close']:
                    sell_score += self.weight * volume_adj * 0.5  # 50% 가중치
                    sell_details.append("Balanced 3일 연속 거래량 증가")
                    
                    # 근거 수집
                    self.technical_evidences.append(
                        self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                               volume_ratio, "Balanced 3일 연속 거래량 증가",
                                               self.weight * volume_adj * 0.5)
                    )
        
        return buy_score, sell_score, buy_details, sell_details 