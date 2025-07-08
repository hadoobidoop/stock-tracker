from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector
from ...models.trading_signal import TechnicalIndicatorEvidence

logger = get_logger(__name__)


class MACDSignalDetector(SignalDetector):
    """MACD 골든/데드 크로스 신호 감지기"""
    
    def __init__(self, weight: float):
        super().__init__(weight, "MACD_Detector")
        self.required_columns = ['MACD_12_26_9', 'MACDs_12_26_9', 'ADX_14']
        # 근거 수집용 리스트 초기화
        self.technical_evidences = []
    
    def detect_signals(self,
                      df: pd.DataFrame,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """MACD 크로스, 추세 지속, 반전 신호를 감지합니다."""

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

        # 조정 계수 가져오기
        trend_follow_buy_adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")
        trend_follow_sell_adj = self.get_adjustment_factor(market_trend, "trend_follow_sell_adj")

        # MACD 근거 생성
        self._collect_macd_evidence(latest_data, prev_data)

        is_golden_cross = prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']
        is_dead_cross = prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] < latest_data['MACDs_12_26_9']

        # --- 매수 신호 로직 ---
        if is_golden_cross:
            macd_cross_buy_score = self.weight * trend_follow_buy_adj
            # ADX 강도에 따른 가중치 조정
            if latest_data['ADX_14'] >= 25:
                macd_cross_buy_score *= 1.2
                buy_details.append(f"MACD 골든 크로스 (ADX 강세: {latest_data['ADX_14']:.2f})")
            elif latest_data['ADX_14'] < 20:
                macd_cross_buy_score *= 0.8
                buy_details.append(f"MACD 골든 크로스 (ADX 약세: {latest_data['ADX_14']:.2f})")
            else:
                buy_details.append(f"MACD 골든 크로스 (ADX 보통: {latest_data['ADX_14']:.2f})")
            
            buy_score += macd_cross_buy_score
            buy_details.append(f"MACD 골든 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} > Signal:{latest_data['MACDs_12_26_9']:.2f})")
        else:
            # 강세 추세 지속
            if latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']:
                continuation_score = self.weight * trend_follow_buy_adj * 0.4  # 40% 가중치
                detail_msg = "MACD 상승 추세 지속"
                if latest_data['MACD_12_26_9'] > 0:
                    continuation_score *= 1.2 # 0선 위에서 가중치 부여
                    detail_msg += " (0선 위)"
                buy_score += continuation_score
                buy_details.append(detail_msg)

            # 상승 반전 (음수 영역에서 상승)
            if prev_data['MACD_12_26_9'] < latest_data['MACD_12_26_9'] < 0:
                buy_score += self.weight * trend_follow_buy_adj * 0.5  # 50% 가중치
                buy_details.append(f"MACD 상승 반전 (MACD: {prev_data['MACD_12_26_9']:.2f} -> {latest_data['MACD_12_26_9']:.2f})")

        # --- 매도 신호 로직 ---
        if is_dead_cross:
            macd_cross_sell_score = self.weight * trend_follow_sell_adj
            # ADX 강도에 따른 가중치 조정
            if latest_data['ADX_14'] >= 25:
                macd_cross_sell_score *= 1.2
                sell_details.append(f"MACD 데드 크로스 (ADX 강세: {latest_data['ADX_14']:.2f})")
            elif latest_data['ADX_14'] < 20:
                macd_cross_sell_score *= 0.8
                sell_details.append(f"MACD 데드 크로스 (ADX 약세: {latest_data['ADX_14']:.2f})")
            else:
                sell_details.append(f"MACD 데드 크로스 (ADX ���통: {latest_data['ADX_14']:.2f})")

            sell_score += macd_cross_sell_score
            sell_details.append(f"MACD 데드 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} < Signal:{latest_data['MACDs_12_26_9']:.2f})")
        else:
            # 약세 추세 지속
            if latest_data['MACD_12_26_9'] < latest_data['MACDs_12_26_9']:
                continuation_score = self.weight * trend_follow_sell_adj * 0.4  # 40% 가중치
                detail_msg = "MACD 하락 추세 지속"
                if latest_data['MACD_12_26_9'] < 0:
                    continuation_score *= 1.2 # 0선 아래에서 가중치 부여
                    detail_msg += " (0선 아래)"
                sell_score += continuation_score
                sell_details.append(detail_msg)

            # 하락 반전 (양수 영역에서 하락)
            if 0 < latest_data['MACD_12_26_9'] < prev_data['MACD_12_26_9']:
                sell_score += self.weight * trend_follow_sell_adj * 0.5  # 50% 가중치
                sell_details.append(f"MACD 하락 반전 (MACD: {prev_data['MACD_12_26_9']:.2f} -> {latest_data['MACD_12_26_9']:.2f})")

        return buy_score, sell_score, buy_details, sell_details
    
    def _collect_macd_evidence(self, latest_data: pd.Series, prev_data: pd.Series):
        """MACD 관련 기술적 지표 근거를 수집합니다."""
        
        # MACD 라인 근거
        macd_evidence = TechnicalIndicatorEvidence(
            indicator_name="MACD_12_26_9",
            current_value=latest_data['MACD_12_26_9'],
            previous_value=prev_data['MACD_12_26_9'],
            threshold_value=latest_data['MACDs_12_26_9'],  # Signal line을 임계값으로 사용
            condition_met=self._determine_macd_condition(latest_data, prev_data),
            timeframe="1h",
            contribution_score=self.weight
        )
        self.technical_evidences.append(macd_evidence)
        
        # Signal 라인 근거
        signal_evidence = TechnicalIndicatorEvidence(
            indicator_name="MACDs_12_26_9",
            current_value=latest_data['MACDs_12_26_9'],
            previous_value=prev_data['MACDs_12_26_9'],
            condition_met="Signal line for MACD crossover",
            timeframe="1h"
        )
        self.technical_evidences.append(signal_evidence)
        
        # ADX 트렌드 강도 근거
        adx_evidence = TechnicalIndicatorEvidence(
            indicator_name="ADX_14",
            current_value=latest_data['ADX_14'],
            previous_value=prev_data['ADX_14'],
            threshold_value=25.0,  # ADX 강도 기준
            condition_met=f"Trend strength: {'Strong' if latest_data['ADX_14'] >= 25 else 'Weak'}",
            timeframe="1h"
        )
        self.technical_evidences.append(adx_evidence)
    
    def _determine_macd_condition(self, latest_data: pd.Series, prev_data: pd.Series) -> str:
        """MACD 조건을 판단합니다."""
        curr_macd = latest_data['MACD_12_26_9']
        prev_macd = prev_data['MACD_12_26_9']
        curr_signal = latest_data['MACDs_12_26_9']
        prev_signal = prev_data['MACDs_12_26_9']
        
        if prev_macd < prev_signal and curr_macd > curr_signal:
            return "Golden Cross - MACD crossed above Signal line"
        elif prev_macd > prev_signal and curr_macd < curr_signal:
            return "Dead Cross - MACD crossed below Signal line"
        elif curr_macd > curr_signal:
            return "MACD above Signal line (bullish)"
        elif curr_macd < curr_signal:
            return "MACD below Signal line (bearish)"
        else:
            return "MACD at Signal line (neutral)"
    
    def get_technical_evidences(self) -> List[TechnicalIndicatorEvidence]:
        """수집된 기술적 지표 근거를 반환합니다."""
        return self.technical_evidences 