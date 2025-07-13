from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.analysis.detectors.trend_following.sma_detector import SMASignalDetector
from domain.analysis.models.trading_signal import TechnicalIndicatorEvidence

logger = get_logger(__name__)


class ConservativeSMADetector(SMASignalDetector):
    """보수적 전략용 SMA 신호 감지기 - 신중한 추세 감지"""
    
    def __init__(self, weight: float):
        super().__init__(weight)
        self.name = "Conservative_SMA_Detector"
        # Conservative 전략은 신중한 설정 사용
        self.adx_threshold = 30  # 더 높은 임계값 (기본 20 → 30)
        self.continuation_weight = 0.2  # 더 낮은 지속 가중치 (기본 0.4 → 0.2)
        self.trend_confirmation_required = True  # 추세 확인 필수
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """보수적인 SMA 신호를 감지합니다."""

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

        # 조정 계수 가져오기 (Conservative는 신중한 조정)
        trend_follow_buy_adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")
        trend_follow_sell_adj = self.get_adjustment_factor(market_trend, "trend_follow_sell_adj")

        is_golden_cross = prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']
        is_dead_cross = prev_data['SMA_5'] > prev_data['SMA_20'] and latest_data['SMA_5'] < latest_data['SMA_20']
        adx_strength = latest_data['ADX_14']

        # --- 매수 신호 로직 ---
        if is_golden_cross:
            sma_cross_buy_score = self.weight * trend_follow_buy_adj * 0.8  # 20% 감소 가중치
            detail_msg = "Conservative SMA 골든 크로스"
            # ADX 강도에 따른 가중치 조정 (신중한 범위)
            if adx_strength >= 35:
                sma_cross_buy_score *= 1.1
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < self.adx_threshold:
                sma_cross_buy_score *= 0.6  # 더 낮은 최소값
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"
            
            buy_score += sma_cross_buy_score
            buy_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")
            
            # 근거 수집
            self.technical_evidences.append(
                self.get_sma_evidence(latest_data['SMA_5'], latest_data['SMA_20'], 
                                    adx_strength, detail_msg, sma_cross_buy_score)
            )
        
        # 상승 추세 지속 (높은 ADX 임계값 사용)
        elif latest_data['SMA_5'] > latest_data['SMA_20']:
            # ADX가 30 이상일 때만 추세 지속으로 인정
            if adx_strength >= self.adx_threshold:
                continuation_score = self.weight * trend_follow_buy_adj * self.continuation_weight * 0.8  # 20% 감소 가중치
                detail_msg = "Conservative SMA 상승 추세 지속"
                if adx_strength >= 35:
                    continuation_score *= 1.1
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                elif adx_strength < self.adx_threshold:
                    continuation_score *= 0.6
                    detail_msg += f" (ADX 약세: {adx_strength:.2f})"
                
                buy_score += continuation_score
                buy_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_sma_evidence(latest_data['SMA_5'], latest_data['SMA_20'], 
                                        adx_strength, detail_msg, continuation_score)
                )
        
        # --- 매도 신호 로직 ---
        if is_dead_cross:
            sma_cross_sell_score = self.weight * trend_follow_sell_adj * 0.8  # 20% 감소 가중치
            detail_msg = "Conservative SMA 데드 크로스"
            # ADX 강도에 따른 가중치 조정 (신중한 범위)
            if adx_strength >= 35:
                sma_cross_sell_score *= 1.1
                detail_msg += f" (ADX 강세: {adx_strength:.2f})"
            elif adx_strength < self.adx_threshold:
                sma_cross_sell_score *= 0.6
                detail_msg += f" (ADX 약세: {adx_strength:.2f})"
            
            sell_score += sma_cross_sell_score
            sell_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")
            
            # 근거 수집
            self.technical_evidences.append(
                self.get_sma_evidence(latest_data['SMA_5'], latest_data['SMA_20'], 
                                    adx_strength, detail_msg, sma_cross_sell_score)
            )
        
        # 하락 추세 지속 (높은 ADX 임계값 사용)
        elif latest_data['SMA_5'] < latest_data['SMA_20']:
            # ADX가 30 이상일 때만 추세 지속으로 인정
            if adx_strength >= self.adx_threshold:
                continuation_score = self.weight * trend_follow_sell_adj * self.continuation_weight * 0.8  # 20% 감소 가중치
                detail_msg = "Conservative SMA 하락 추세 지속"
                if adx_strength >= 35:
                    continuation_score *= 1.1
                    detail_msg += f" (ADX 강세: {adx_strength:.2f})"
                elif adx_strength < self.adx_threshold:
                    continuation_score *= 0.6
                    detail_msg += f" (ADX 약세: {adx_strength:.2f})"
                
                sell_score += continuation_score
                sell_details.append(f"{detail_msg} (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")
                
                # 근거 수집
                self.technical_evidences.append(
                    self.get_sma_evidence(latest_data['SMA_5'], latest_data['SMA_20'], 
                                        adx_strength, detail_msg, continuation_score)
                )
        
        return buy_score, sell_score, buy_details, sell_details