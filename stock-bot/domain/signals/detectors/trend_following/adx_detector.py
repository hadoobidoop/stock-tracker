from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.config.signals.signal_weights import SIGNAL_WEIGHTS
from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ADXSignalDetector(SignalDetector):
    """ADX 강한 추세 신호 감지기 - 파라미터 주입 방식 지원"""
    
    def __init__(self, weight: float = None, name: str = None, parameters: Optional[Dict] = None):
        weight = weight or SIGNAL_WEIGHTS["adx_strong_trend"]
        super().__init__(weight, name or "ADX_Detector")
        self.required_columns = ['ADX_14', 'DMP_14', 'DMN_14']
        
        # 기본 파라미터 설정
        default_params = {
            'adx_strong_threshold': 25,    # ADX 강한 추세 임계값
            'adx_weak_threshold': 20,      # ADX 약한 추세 임계값
            'weak_trend_multiplier': 0.5,  # 약한 추세시 가중치
            'strong_trend_bonus': 1.2,     # 강한 추세시 보너스
            'di_diff_threshold': 5         # DI 차이 최소 임계값
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
    
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
        
        adx_value = latest_data['ADX_14']
        dmp_value = latest_data.get('DMP_14', 0)
        dmn_value = latest_data.get('DMN_14', 0)
        
        # ADX 강도에 따른 신호 생성
        if adx_value >= self.params['adx_strong_threshold']:
            # DI 차이가 충분한지 확인
            di_diff = abs(dmp_value - dmn_value)
            if di_diff >= self.params['di_diff_threshold']:
                signal_strength = min((adx_value - self.params['adx_strong_threshold']) / 10, 1.0)
                base_score = self.weight * (1 + signal_strength * self.params['strong_trend_bonus'])
                
                # +DI > -DI: 강한 상승 추세
                if dmp_value > dmn_value:
                    buy_score += base_score * trend_follow_buy_adj
                    buy_details.append(f"ADX 강한 상승 추세 (ADX:{adx_value:.2f}, +DI:{dmp_value:.2f})")
                
                # -DI > +DI: 강한 하락 추세
                elif dmn_value > dmp_value:
                    sell_score += base_score * trend_follow_sell_adj
                    sell_details.append(f"ADX 강한 하락 추세 (ADX:{adx_value:.2f}, -DI:{dmn_value:.2f})")
            else:
                # DI 차이가 작으면 약한 신호로 처리
                base_score = self.weight * self.params['weak_trend_multiplier']
                
                if dmp_value > dmn_value:
                    buy_score += base_score * trend_follow_buy_adj
                    buy_details.append(f"ADX 상승 추세 (DI 차이 작음: {di_diff:.2f})")
                elif dmn_value > dmp_value:
                    sell_score += base_score * trend_follow_sell_adj
                    sell_details.append(f"ADX 하락 추세 (DI 차이 작음: {di_diff:.2f})")
        
        elif adx_value >= self.params['adx_weak_threshold']:
            # 약한 추세 구간
            base_score = self.weight * self.params['weak_trend_multiplier']
            
            if dmp_value > dmn_value:
                buy_score += base_score * trend_follow_buy_adj
                buy_details.append(f"ADX 약한 상승 추세 ({adx_value:.2f})")
            elif dmn_value > dmp_value:
                sell_score += base_score * trend_follow_sell_adj
                sell_details.append(f"ADX 약한 하락 추세 ({adx_value:.2f})")
        
        return buy_score, sell_score, buy_details, sell_details 