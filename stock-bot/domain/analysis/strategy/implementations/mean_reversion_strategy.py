from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType
from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector
from domain.analysis.detectors.volatility.bb_detector import BBSignalDetector
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None

    def initialize(self) -> bool:
        try:
            detectors = [
                BBSignalDetector(weight=6.0, detector_type="mean_reversion"),
                RSISignalDetector(weight=4.0),
                StochSignalDetector(weight=3.0),
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

            # MeanReversion 특화 점수 조정 (UniversalStrategy와 동일)
            if market_trend == TrendType.NEUTRAL:
                score *= 1.15

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

            # === 장기추세 가중치 적용 ===
            buy_score = signal_result.get('buy_score', 0.0)
            sell_score = signal_result.get('sell_score', 0.0)
            if long_term_trend == TrendType.BULLISH:
                buy_score *= 1.2
            elif long_term_trend == TrendType.BEARISH:
                sell_score *= 1.2
            # ============================

            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=has_signal,
                total_score=score,
                signal_strength="",
                signals_detected=signal_result.get('details', []),
                signal=trading_signal,
                buy_score=buy_score,
                sell_score=sell_score,
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
