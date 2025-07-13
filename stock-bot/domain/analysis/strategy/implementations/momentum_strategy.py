from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from strategy.configs.static_strategies import StrategyConfig, StrategyType
from domain.analysis.detectors.composite.composite_detector import CompositeSignalDetector
from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector
from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    RSI, 스토캐스틱 등 모멘텀 지표를 중심으로 신호를 감지하는 전략.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None

    def initialize(self) -> bool:
        """
        모멘텀 전략에 필요한 SignalDetector와 Orchestrator를 생성하고 초기화합니다.
        """
        try:
            detectors = [
                RSISignalDetector(weight=6.0),
                StochSignalDetector(weight=5.0),
                MACDSignalDetector(weight=4.0),
                VolumeSignalDetector(weight=3.0),
                CompositeSignalDetector(
                    detectors=[
                        RSISignalDetector(weight=0),
                        StochSignalDetector(weight=0)
                    ],
                    weight=8.0,
                    require_all=True,
                    name="RSI_Stoch_Confirm"
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
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")

        self.last_analysis_time = pd.Timestamp.now(tz='UTC')

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

            # Momentum 특화 점수 조정 (UniversalStrategy와 동일)
            if market_trend == TrendType.BULLISH:
                score *= 1.15
            elif market_trend == TrendType.BEARISH:
                score *= 0.9

            # 성능 지표 업데이트
            self.score_history.append(score)
            if len(self.score_history) > 100:
                self.score_history.pop(0)
            if self.score_history:
                self.average_score = sum(self.score_history) / len(self.score_history)

            trading_signal = None
            if has_signal:
                self.signals_generated += 1
                trading_signal = self._create_trading_signal(
                    signal_result, ticker, score, df_with_indicators
                )

            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=has_signal,
                total_score=score,
                signal_strength="",
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
