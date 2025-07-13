from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
from domain.analysis.models.trading_signal import TechnicalIndicatorEvidence

logger = get_logger(__name__)


class AggressiveVolumeDetector(VolumeSignalDetector):
    """공격적 전략용 거래량 신호 감지기 - 민감한 신호 감지"""
    
    def __init__(self, weight: float):
        super().__init__(weight)
        self.name = "Aggressive_Volume_Detector"
        # Aggressive 전략은 민감한 설정 사용
        self.volume_surge_threshold = 1.3  # 더 낮은 임계값 (기본 1.5 → 1.3)
        self.volume_trend_days = 2  # 더 짧은 기간 (기본 3 → 2)
        self.volume_confirmation_required = False  # 거래량 확인 불필요
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """공격적인 거래량 신호를 감지합니다."""
        
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
        
        # 조정 계수 가져오기 (Aggressive는 강한 조정)
        volume_adj = self.get_adjustment_factor(market_trend, "volume_adj")
        
        # 거래량 급증 (낮은 임계값 사용)
        volume_ratio = latest_data['Volume'] / latest_data['Volume_SMA_20']
        
        if volume_ratio > self.volume_surge_threshold:
            # 거래량 급증 강도 계산 (더 민감한 범위)
            volume_strength = min((volume_ratio - self.volume_surge_threshold) / self.volume_surge_threshold, 1.5)
            
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                # 상승폭에 따른 추가 가중치 (더 민감한 범위)
                price_change_pct = (latest_data['Close'] - prev_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 150, 2.0)  # 최대 2% 상승까지
                
                buy_score += self.weight * volume_adj * (1.2 + volume_strength + price_strength)  # 20% 추가 가중치
                buy_details.append(
                    f"Aggressive 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                           volume_ratio, f"Aggressive 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})",
                                           self.weight * volume_adj * (1.2 + volume_strength + price_strength))
                )
            
            # 하락 시 거래량 급증
            elif latest_data['Close'] < prev_data['Close']:
                # 하락폭에 따른 추가 가중치 (더 민감한 범위)
                price_change_pct = (prev_data['Close'] - latest_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 150, 2.0)  # 최대 2% 하락까지
                
                sell_score += self.weight * volume_adj * (1.2 + volume_strength + price_strength)  # 20% 추가 가중치
                sell_details.append(
                    f"Aggressive 하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                           volume_ratio, f"Aggressive 하락 시 거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f} * {self.volume_surge_threshold})",
                                           self.weight * volume_adj * (1.2 + volume_strength + price_strength))
                )
        
        # 거래량 증가 추세 (짧은 기간 사용)
        elif len(df) >= 3:
            vol_2d = df['Volume'].iloc[-2:].values
            if all(vol_2d[i] > vol_2d[i-1] for i in range(1, len(vol_2d))):
                # 상승 시 거래량 증가 추세
                if latest_data['Close'] > prev_data['Close']:
                    buy_score += self.weight * volume_adj * 0.8  # 80% 가중치 (높음)
                    buy_details.append("Aggressive 2일 연속 거래량 증가")
                    
                    # 근거 수집
                    self.technical_evidences.append(
                        self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                               volume_ratio, "Aggressive 2일 연속 거래량 증가",
                                               self.weight * volume_adj * 0.8)
                    )
                # 하락 시 거래량 증가 추세
                elif latest_data['Close'] < prev_data['Close']:
                    sell_score += self.weight * volume_adj * 0.8  # 80% 가중치
                    sell_details.append("Aggressive 2일 연속 거래량 증가")
                    
                    # 근거 수집
                    self.technical_evidences.append(
                        self.get_volume_evidence(latest_data['Volume'], latest_data['Volume_SMA_20'],
                                               volume_ratio, "Aggressive 2일 연속 거래량 증가",
                                               self.weight * volume_adj * 0.8)
                    )
        
        return buy_score, sell_score, buy_details, sell_details 