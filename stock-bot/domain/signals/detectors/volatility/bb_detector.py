from typing import Dict, List, Tuple, Optional

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BBSignalDetector(SignalDetector):
    """
    볼린저 밴드 신호 감지기 - 파라미터 주입 방식 지원
    - 평균 회귀 신호 (과매수/과매도)
    - 변동성 돌파 신호
    """

    def __init__(self, weight: float, name: str = None, parameters: Optional[Dict] = None):
        super().__init__(weight, name or "BB_Detector")
        self.required_columns = ['BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0', 'BBB_20_2.0']
        
        # 기본 파라미터 설정
        default_params = {
            'detector_type': 'mean_reversion',  # 'mean_reversion' 또는 'breakout'
            'base_state_weight': 0.5,           # 기본 상태 신호 가중치
            'event_bonus_weight': 0.5,          # 이벤트 보너스 가중치
            'continuation_weight': 0.5,         # 지속 상태 가중치
            'squeeze_quantile': 0.1,            # squeeze 판단 퀀타일
            'squeeze_lookback_period': 50,      # squeeze 판단을 위한 롤링 기간
            'require_momentum_confirmation': True,  # 모멘텀 확인 필요 여부
            'strength_amplification': 1.0       # 강도 증폭 계수
        }
        
        # 외부 파라미터와 기본값 병합
        self.params = {**default_params, **(parameters or {})}
        self.detector_type = self.params['detector_type']

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
            weight_multiplier = self.params['base_state_weight'] + (strength * self.params['strength_amplification'])
            buy_score += self.weight * adj * weight_multiplier
            buy_details.append(f"BB 하단 이탈 상태 (Price: {latest['Close']:.2f})")
            
            # 이벤트: 하단 밴드 안으로 복귀 시 추가 점수
            if prev['Close'] < prev['BBL_20_2.0'] and latest['Close'] > latest['BBL_20_2.0']:
                buy_score += self.weight * adj * self.params['event_bonus_weight']
                buy_details.append("BB 하단 복귀 이벤트")

        # 매도 신호: 상단 밴드 근접 또는 터치
        if latest['Close'] > latest['BBU_20_2.0']:
            strength = (latest['Close'] - latest['BBU_20_2.0']) / latest['BBB_20_2.0']
            weight_multiplier = self.params['base_state_weight'] + (strength * self.params['strength_amplification'])
            sell_score += self.weight * adj * weight_multiplier
            sell_details.append(f"BB 상단 이탈 상태 (Price: {latest['Close']:.2f})")

            # 이벤트: 상단 밴드 안으로 복귀 시 추가 점수
            if prev['Close'] > prev['BBU_20_2.0'] and latest['Close'] < latest['BBU_20_2.0']:
                sell_score += self.weight * adj * self.params['event_bonus_weight']
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
        squeeze_threshold = df['BBB_20_2.0'].rolling(self.params['squeeze_lookback_period']).quantile(self.params['squeeze_quantile']).iloc[-1]
        is_squeezed = latest['BBB_20_2.0'] < squeeze_threshold
        
        # 매수 신호: 상단 밴드 돌파 이벤트 또는 지속
        is_breakout_buy_event = prev['Close'] < prev['BBU_20_2.0'] and latest['Close'] > latest['BBU_20_2.0']
        is_breakout_buy_state = latest['Close'] > latest['BBU_20_2.0']

        if is_squeezed and is_breakout_buy_event:
            buy_score += self.weight * adj # 돌파 이벤트
            buy_details.append(f"BB Squeeze 후 상단 돌파 이벤트 (Bandwidth: {latest['BBB_20_2.0']:.4f})")
        elif is_breakout_buy_state:
            momentum_check = not self.params['require_momentum_confirmation'] or latest['Close'] > prev['Close']
            if momentum_check:
                buy_score += self.weight * adj * self.params['continuation_weight'] # 돌파 지속 상태
                buy_details.append(f"BB 상단 돌파 지속 상태 (Price: {latest['Close']:.2f})")

        # 매도 신호: 하단 밴드 돌파 이벤트 또는 지속
        is_breakout_sell_event = prev['Close'] > prev['BBL_20_2.0'] and latest['Close'] < latest['BBL_20_2.0']
        is_breakout_sell_state = latest['Close'] < latest['BBL_20_2.0']

        if is_squeezed and is_breakout_sell_event:
            sell_score += self.weight * adj
            sell_details.append(f"BB Squeeze 후 하단 돌파 이벤트 (Bandwidth: {latest['BBB_20_2.0']:.4f})")
        elif is_breakout_sell_state:
            momentum_check = not self.params['require_momentum_confirmation'] or latest['Close'] < prev['Close']
            if momentum_check:
                sell_score += self.weight * adj * self.params['continuation_weight'] # 돌파 지속 상태
                sell_details.append(f"BB 하단 돌파 지속 상태 (Price: {latest['Close']:.2f})")

        return buy_score, sell_score, buy_details, sell_details 