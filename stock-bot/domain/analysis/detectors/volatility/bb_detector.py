from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class BBSignalDetector(SignalDetector):
    """
    볼린저 밴드 신호 감지기
    - 평균 회귀 신호 (과매수/과매도)
    - 변동성 돌파 신호
    """

    def __init__(self, weight: float, detector_type: str = "mean_reversion"):
        super().__init__(weight, "BB_Detector")
        self.required_columns = ['BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0', 'BBB_20_2.0']
        self.detector_type = detector_type  # 'mean_reversion' 또는 'breakout'

    def detect_signals(self,
                       df: pd.DataFrame,
                       market_trend: TrendType = TrendType.NEUTRAL,
                       long_term_trend: TrendType = TrendType.NEUTRAL,
                       daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:

        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []

        if self.detector_type == "mean_reversion":
            return self._detect_mean_reversion(df, market_trend)
        elif self.detector_type == "breakout":
            return self._detect_breakout(df, market_trend)
        else:
            return 0.0, 0.0, [], []

    def _detect_mean_reversion(self, df: pd.DataFrame, market_trend: TrendType) -> Tuple[float, float, List[str], List[str]]:
        """평균 회귀 신호 감지"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        buy_score, sell_score = 0.0, 0.0
        buy_details, sell_details = [], []

        adj = self.get_adjustment_factor(market_trend, "momentum_reversal_adj")

        # 매수 신호: 하단 밴드 터치 후 반등
        if prev['Close'] < prev['BBL_20_2.0'] and latest['Close'] > latest['BBL_20_2.0']:
            buy_score += self.weight * adj
            buy_details.append(f"BB 하단 터치 후 반등 (Price: {latest['Close']:.2f})")

        # 매도 신호: 상단 밴드 터치 후 하락
        if prev['Close'] > prev['BBU_20_2.0'] and latest['Close'] < latest['BBU_20_2.0']:
            sell_score += self.weight * adj
            sell_details.append(f"BB 상단 터치 후 하락 (Price: {latest['Close']:.2f})")

        return buy_score, sell_score, buy_details, sell_details

    def _detect_breakout(self, df: pd.DataFrame, market_trend: TrendType) -> Tuple[float, float, List[str], List[str]]:
        """변동성 돌파 신호 감지"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        buy_score, sell_score = 0.0, 0.0
        buy_details, sell_details = [], []

        adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")

        # 볼린저 밴드 폭(BBB)이 매우 좁은 상태인지 확인 (지난 50일간 하위 10% 수준)
        is_squeezed = latest['BBB_20_2.0'] < df['BBB_20_2.0'].rolling(50).quantile(0.1).iloc[-1]

        if is_squeezed:
            # 매수 신호: 상단 밴드 돌파
            if prev['Close'] < prev['BBU_20_2.0'] and latest['Close'] > latest['BBU_20_2.0']:
                buy_score += self.weight * adj
                buy_details.append(f"BB Squeeze 후 상단 돌파 (Bandwidth: {latest['BBB_20_2.0']:.4f})")

            # 매도 신호: 하단 밴드 돌파
            if prev['Close'] > prev['BBL_20_2.0'] and latest['Close'] < latest['BBL_20_2.0']:
                sell_score += self.weight * adj
                sell_details.append(f"BB Squeeze 후 하단 돌파 (Bandwidth: {latest['BBB_20_2.0']:.4f})")

        return buy_score, sell_score, buy_details, sell_details 