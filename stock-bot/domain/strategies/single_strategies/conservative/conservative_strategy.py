from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.models.enums import StrategyType
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.detectors.composite.composite_detector import CompositeSignalDetector
from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.conservative_config import ConservativeStrategyConfig
from .detectors.conservative_sma_detector import ConservativeSMADetector
from .detectors.conservative_volume_detector import ConservativeVolumeDetector

logger = get_logger(__name__)


class ConservativeStrategy(BaseStrategy):
    """
    Conservative(보수적) 전략 - 신뢰도 최우선, 신호 빈도 최소화

    [구조 및 특징]
    - 커스텀 Detector: ConservativeSMADetector, ConservativeVolumeDetector
    - 기본 Detector: MACDSignalDetector
    - Composite Detector: MACD+Volume 컨펌(신호 신뢰도 강화)
    - Detector별 가중치는 config.detector_weights에서 관리
    - 점수는 score_multiplier(기본 0.8)로 20% 감소(매우 보수적)
    - 장기추세(BULLISH/BEARISH) 가중치 적용

    [주요 파라미터]
    - signal_threshold: 신호 발생 기준점(기본 12.0)
    - detector_weights: 각 Detector별 가중치(Composite > SMA/MACD > Volume)
    - score_multiplier: 점수 조정(기본 0.8)
    - max_positions/position_hold_hours: 포지션 관리(2개/5일)

    [사용 예시]
        config = ConservativeStrategyConfig()
        strategy = ConservativeStrategy(StrategyType.CONSERVATIVE, config)
        strategy.initialize()
        result = strategy.analyze(df, ticker, market_trend, long_term_trend)

    [반환값]
    - StrategyResult: 신호 발생 여부, 점수, 근거, buy/sell score, stop_loss 등 포함
    """
    def __init__(self, strategy_type: StrategyType, config: ConservativeStrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None
        self.config = config

    def initialize(self) -> bool:
        """
        Conservative 전략의 Detector 조합 및 orchestrator 초기화
        - 커스텀 Detector: ConservativeSMADetector, ConservativeVolumeDetector
        - 기본 Detector: MACDSignalDetector
        - Composite Detector: MACD+Volume 컨펌(신호 신뢰도 강화)
        - Detector별 가중치는 config.detector_weights에서 관리
        """
        try:
            detectors = [
                ConservativeSMADetector(weight=self.config.detector_weights['sma']),
                MACDSignalDetector(weight=self.config.detector_weights['macd']),
                ConservativeVolumeDetector(weight=self.config.detector_weights['volume']),
                CompositeSignalDetector(
                    detectors=[
                        MACDSignalDetector(weight=0),
                        ConservativeVolumeDetector(weight=0)
                    ],
                    weight=self.config.detector_weights['composite'],
                    require_all=True,
                    name="Conservative_MACD_Volume_Confirm"
                )
            ]
            self.orchestrator = SignalDetectionOrchestrator()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (커스텀 Detector 사용)")
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
        Conservative 전략의 신호 분석 및 결과 반환
        - 쿨다운 체크, orchestrator 기반 신호/점수/근거 수집
        - score_multiplier(0.8)로 점수 20% 감소(매우 보수적)
        - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
        - 예외 발생 시 안전하게 실패 반환
        """
        current_time = pd.Timestamp.now(tz='UTC')
        if not self.can_generate_signal(current_time):
            logger.debug(f"{self.get_name()} 쿨다운 중 - 신호 생성 스킵")
            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=False,
                total_score=0.0,
                signal_strength="WEAK",
                signals_detected=[],
            )
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")
        self.last_analysis_time = current_time
        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )
            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)
            # Conservative 특화 점수 조정
            original_score = score
            score *= self.config.score_multiplier  # 0.8배(매우 보수적)
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
                logger.info(f"{self.get_name()} 신호 생성: {signal_result.get('type')} (점수: {original_score:.2f} → {score:.2f})")
            # === 장기추세 가중치 적용 ===
            buy_score = signal_result.get('buy_score', 0.0)
            sell_score = signal_result.get('sell_score', 0.0)
            if long_term_trend == TrendType.BULLISH:
                buy_score *= self.config.long_term_bullish_multiplier
            elif long_term_trend == TrendType.BEARISH:
                sell_score *= self.config.long_term_bearish_multiplier
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
