from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector
from domain.signals.detectors.trend_following.adx_detector import ADXSignalDetector
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from domain.strategies.strategy_config import StrategyConfig
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.trend_pullback_config import SMA_WEIGHT, ADX_WEIGHT, RSI_WEIGHT

logger = get_logger(__name__)


class TrendPullbackStrategy(BaseStrategy):
    """
    상승 추세 중 일시적 하락(눌림목) 시 매수하는 전략.
    - 중앙 Detector(SMA, ADX, RSI) + 파라미터 주입 방식
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalProcessor] = None

    def initialize(self) -> bool:
        try:
            # TrendPullback 전략용 파라미터 설정
            trend_pullback_sma_params = {
                'adx_threshold': 20,  # 기본 20 유지
                'continuation_weight': 0.5,  # 기본 0.4에서 더 보수적으로
                'trend_confirmation_required': True,  # 추세 확인 필요
                'pullback_mode': True  # 눌림목 모드 활성화
            }
            
            trend_pullback_adx_params = {
                'adx_threshold': 25,  # 기본 25 유지
                'trend_strength_required': True,  # 추세 강도 확인 필요
                'pullback_mode': True  # 눌림목 모드 활성화
            }
            
            trend_pullback_rsi_params = {
                'oversold_threshold': 40,  # 기본 35에서 더 관대하게
                'overbought_threshold': 60,  # 기본 65에서 더 관대하게
                'pullback_mode': True  # 눌림목 모드 활성화
            }
            
            detectors = [
                SMASignalDetector(
                    weight=SMA_WEIGHT,
                    name="TrendPullback_SMA_Detector",
                    parameters=trend_pullback_sma_params
                ),
                ADXSignalDetector(
                    weight=ADX_WEIGHT,
                    name="TrendPullback_ADX_Detector",
                    parameters=trend_pullback_adx_params
                ),
                RSISignalDetector(
                    weight=RSI_WEIGHT,
                    name="TrendPullback_RSI_Detector",
                    parameters=trend_pullback_rsi_params
                )
            ]
            self.orchestrator = SignalProcessor()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (중앙 Detector + 파라미터 주입)")
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

        logger.debug(f"[TrendPullback] 분석 시작 | ticker={ticker} | market_trend={market_trend} | long_term_trend={long_term_trend}")

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

            # TrendPullback 특화 점수 조정 (UniversalStrategy와 동일)
            if market_trend == long_term_trend:
                score *= 1.1
                logger.debug(f"[TrendPullback] 시장/장기 추세 일치: score 1.1배 적용")
            else:
                score *= 0.9
                logger.debug(f"[TrendPullback] 시장/장기 추세 불일치: score 0.9배 적용")

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

            logger.info(
                f"[TrendPullback] 분석결과 | ticker={ticker} | has_signal={has_signal} | score={score:.2f} | "
                f"buy_score={signal_result.get('buy_score', 0.0):.2f} | sell_score={signal_result.get('sell_score', 0.0):.2f} | "
                f"signal_details={signal_result.get('details', [])}"
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
