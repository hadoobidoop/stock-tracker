from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_orchestrator import SignalDetectionOrchestrator
from domain.strategies.strategy_config import StrategyConfig
from domain.signals.models.enums import StrategyType
from domain.signals.detectors.composite.composite_detector import CompositeSignalDetector
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.trend_following_config import SMA_WEIGHT, MACD_WEIGHT, ADX_WEIGHT, VOLUME_WEIGHT
from .detectors.trend_following_adx_detector import ADXSignalDetector
from .detectors.trend_following_macd_detector import MACDSignalDetector
from .detectors.trend_following_sma_detector import SMASignalDetector
from .detectors.trend_following_volume_detector import VolumeSignalDetector

logger = get_logger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following(추세추종) 전략 - SMA, MACD, ADX 등 추세 지표 기반

    [구조 및 특징]
    - 커스텀 Detector: trend_following_sma_detector, trend_following_macd_detector, trend_following_adx_detector, trend_following_volume_detector
    - Composite Detector: MACD+Volume 컨펌(신호 신뢰도 강화)
    - Detector별 가중치는 코드 내에서 직접 관리(예: SMA 7.0, MACD 6.0 등)
    - 시장/장기 추세 일치(trend_alignment) 필터 적용 가능
    - 점수는 시장/장기 추세 일치 여부에 따라 가중치 조정

    [주요 파라미터]
    - signal_threshold: 신호 발생 기준점(기본 7.0)
    - detector별 가중치: SMA(7.0), MACD(6.0), ADX(6.0), Volume(4.0), Composite(8.0)
    - trend_alignment: 시장/장기 추세 일치 필터(설정에서 on/off)

    [사용 예시]
        strategy = TrendFollowingStrategy(StrategyType.TREND_FOLLOWING, config)
        strategy.initialize()
        result = strategy.analyze(df, ticker, market_trend, long_term_trend)

    [반환값]
    - StrategyResult: 신호 발생 여부, 점수, 근거, buy/sell score, stop_loss 등 포함
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None

    def initialize(self) -> bool:
        """
        Trend Following 전략의 Detector 조합 및 orchestrator 초기화
        - 커스텀 Detector: trend_following_sma_detector, trend_following_macd_detector, trend_following_adx_detector, trend_following_volume_detector
        - Composite Detector: MACD+Volume 컨펌(신호 신뢰도 강화)
        - Detector별 가중치는 코드 내에서 직접 관리
        """
        try:
            # 설정 파일에 정의된 detector들을 코드로 직접 생성
            detectors = [
                SMASignalDetector(weight=SMA_WEIGHT),
                MACDSignalDetector(weight=MACD_WEIGHT),
                ADXSignalDetector(weight=ADX_WEIGHT),
                VolumeSignalDetector(weight=VOLUME_WEIGHT),
                CompositeSignalDetector(
                    detectors=[
                        MACDSignalDetector(weight=0),  # 가중치는 CompositeDetector에서 관리
                        VolumeSignalDetector(weight=0)
                    ],
                    weight=8.0,
                    require_all=True,
                    name="MACD_Volume_Confirm"
                )
            ]
            self.orchestrator = SignalDetectionOrchestrator()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"{self.get_name()} 초기화 실패: {e}")
            self.is_initialized = False
            return False

    def analyze(self,
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Optional[Dict] = None) -> StrategyResult:
        """
        Trend Following 전략의 신호 분석 및 결과 반환
        - 내부 orchestrator 기반 신호/점수/근거 수집
        - 시장/장기 추세 일치 여부에 따라 점수 가중치 조정
        - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
        - 예외 발생 시 안전하게 실패 반환
        """
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")

        self.last_analysis_time = pd.Timestamp.now(tz='UTC')

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            base_score = signal_result.get('score', 0)
            has_signal = bool(signal_result and signal_result.get('type'))

            # TrendFollowing 특화 점수 조정 (UniversalStrategy와 동일)
            if has_signal:
                if market_trend == long_term_trend:
                    adjusted_score = base_score * 1.1
                else:
                    adjusted_score = base_score * 0.9
            else:
                adjusted_score = 0.0

            # 성능 지표 업데이트
            self.score_history.append(adjusted_score)
            if len(self.score_history) > 100:
                self.score_history.pop(0)
            if self.score_history:
                self.average_score = sum(self.score_history) / len(self.score_history)

            trading_signal = None
            if has_signal:
                self.signals_generated += 1
                trading_signal = self._create_trading_signal(
                    signal_result, ticker, adjusted_score, df_with_indicators
                )

            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=has_signal,
                total_score=adjusted_score,
                signal_strength="",  # post_init에서 자동 계산
                signals_detected=signal_result.get('details', []),
                signal=trading_signal,
                buy_score=signal_result.get('buy_score', 0.0),
                sell_score=signal_result.get('sell_score', 0.0),
                stop_loss_price=signal_result.get('stop_loss_price')
            )

        except Exception as e:
            logger.error(f"{self.get_name()} 분석 실패: {e}")
            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=False,
                total_score=0.0,
                signal_strength="WEAK",
                signals_detected=[],
            )

    def _adjust_score(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """
        Trend Following 전략에 특화된 점수 조정 로직
        - 시장/장기 추세 일치 시 가중치 부여, 불일치 시 점수 감소 또는 무효화
        """
        adjusted_score = base_score

        # 시장 추세와 장기 추세가 모두 상승세일 때 가중치 부여
        if market_trend == TrendType.BULLISH and long_term_trend == TrendType.BULLISH:
            adjusted_score *= 1.2
        # 시장 추세와 장기 추세가 모두 하락세일 때 점수 감소
        elif market_trend == TrendType.BEARISH and long_term_trend == TrendType.BEARISH:
            adjusted_score *= 0.8

        # 추세 일치 필터 (이 전략의 핵심)
        if self.config.market_filters.get('trend_alignment', False):
            if market_trend != long_term_trend:
                return 0.0  # 추세가 일치하지 않으면 신호 무효화

        return adjusted_score
