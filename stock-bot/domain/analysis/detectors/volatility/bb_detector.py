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
        """평균 회귀 신호 (상태 + 이벤트) 감지"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        buy_score, sell_score = 0.0, 0.0
        buy_details, sell_details = [], []

        adj = self.get_adjustment_factor(market_trend, "momentum_reversal_adj")

        # 매수 신호: 하단 밴드 근접 또는 터치
        if latest['Close'] < latest['BBL_20_2.0']:
            # 밴드 밖으로 나간 정도에 따라 점수 차등
            strength = (latest['BBL_20_2.0'] - latest['Close']) / latest['BBB_20_2.0']
            buy_score += self.weight * adj * (0.5 + strength) # 상태 점수
            buy_details.append(f"BB 하단 이탈 상태 (Price: {latest['Close']:.2f})")
            
            # 이벤트: 하단 밴드 안으로 복귀 시 추가 점수
            if prev['Close'] < prev['BBL_20_2.0'] and latest['Close'] > latest['BBL_20_2.0']:
                buy_score += self.weight * adj * 0.5 # 이벤트 보너스
                buy_details.append("BB 하단 복귀 이벤트")

        # 매도 신호: 상단 밴드 근접 ���는 터치
        if latest['Close'] > latest['BBU_20_2.0']:
            strength = (latest['Close'] - latest['BBU_20_2.0']) / latest['BBB_20_2.0']
            sell_score += self.weight * adj * (0.5 + strength) # 상태 점수
            sell_details.append(f"BB 상단 이탈 상태 (Price: {latest['Close']:.2f})")

            # 이벤트: 상단 밴드 안으로 복귀 시 추가 점수
            if prev['Close'] > prev['BBU_20_2.0'] and latest['Close'] < latest['BBU_20_2.0']:
                sell_score += self.weight * adj * 0.5 # 이벤트 보너스
                sell_details.append("BB 상단 복귀 이벤트")

        return buy_score, sell_score, buy_details, sell_details

    def _detect_breakout(self, df: pd.DataFrame, market_trend: TrendType) -> Tuple[float, float, List[str], List[str]]:
        """변동성 돌파 신호 (이벤트 + 지속 상태) 감지"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        buy_score, sell_score = 0.0, 0.0
        buy_details, sell_details = [], []

        adj = self.get_adjustment_factor(market_trend, "trend_follow_buy_adj")

        # 볼린저 밴드 폭(BBB)이 매우 좁은 상태인지 확인 (Squeeze)
        is_squeezed = latest['BBB_20_2.0'] < df['BBB_20_2.0'].rolling(50).quantile(0.1).iloc[-1]
        
        # 매수 신호: 상단 밴드 돌파 이벤트 또는 지속
        is_breakout_buy_event = prev['Close'] < prev['BBU_20_2.0'] and latest['Close'] > latest['BBU_20_2.0']
        is_breakout_buy_state = latest['Close'] > latest['BBU_20_2.0']

        if is_squeezed and is_breakout_buy_event:
            buy_score += self.weight * adj # 돌파 이벤트
            buy_details.append(f"BB Squeeze 후 상단 돌파 이벤트 (Bandwidth: {latest['BBB_20_2.0']:.4f})")
        elif is_breakout_buy_state and latest['Close'] > prev['Close']:
            buy_score += self.weight * adj * 0.5 # 돌파 지속 상태
            buy_details.append(f"BB 상단 돌파 지속 상태 (Price: {latest['Close']:.2f})")

        # 매도 신호: 하단 밴드 돌파 이벤트 또는 지속
        is_breakout_sell_event = prev['Close'] > prev['BBL_20_2.0'] and latest['Close'] < latest['BBL_20_2.0']
        is_breakout_sell_state = latest['Close'] < latest['BBL_20_2.0']

        if is_squeezed and is_breakout_sell_event:
            sell_score += self.weight * adj
            sell_details.append(f"BB Squeeze 후 하단 돌파 이벤트 (Bandwidth: {latest['BBB_20_2.0']:.4f})")
        elif is_breakout_sell_state and latest['Close'] < prev['Close']:
            sell_score += self.weight * adj * 0.5 # 돌파 지속 상태
            sell_details.append(f"BB 하단 돌파 지속 상태 (Price: {latest['Close']:.2f})")

        return buy_score, sell_score, buy_details, sell_details 