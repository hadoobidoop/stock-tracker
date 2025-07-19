"""
mean_reversion 전략 실행체 (독립 패키지)

- BB(볼린저밴드, mean_reversion), RSI, Stoch Detector를 config 기반으로 동적으로 조합
- Detector별 가중치/파라미터는 config에서 일관 관리 (유지보수/튜닝/확장성 우수)
- mean_reversion 전용 래퍼 Detector 클래스 사용 (prefix: MeanReversion)
- signal_threshold: 7.0 (표준), position_management: 최대 4개, 24시간 보유(단기)
- config: domain.strategies.mean_reversion.configs.mean_reversion_config.MeanReversionStrategyConfig

활용 포인트:
    - 과매수/과매도 후 평균 회귀 신호 포착
    - 단기/중기 변동성 구간에서 mean reversion 기회 탐지
    - 각 Detector의 근거(TechnicalIndicatorEvidence) 상세 기록
    - Detector 추가/변경 시 config만 수정하면 자동 반영
"""
from typing import Dict, Optional

import pandas as pd

from domain.signals.models.enums import StrategyType
from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from domain.strategies.single.mean_reversion.configs.mean_reversion_config import MeanReversionStrategyConfig
from domain.strategies.single.mean_reversion.detectors.mean_reversion_bb_detector import MeanReversionBBSignalDetector
from domain.strategies.single.mean_reversion.detectors.mean_reversion_rsi_detector import MeanReversionRSISignalDetector
from domain.strategies.single.mean_reversion.detectors.mean_reversion_stoch_detector import MeanReversionStochSignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)

class MeanReversionStrategy(BaseStrategy):
    """
    mean_reversion 전략 실행체
    - config 기반 동적 Detector 조합 (BB, RSI, Stoch)
    - Detector별 가중치/파라미터는 config에서 관리
    - mean_reversion 전용 래퍼 Detector 클래스 사용
    """
    def __init__(self, strategy_type: StrategyType = StrategyType.MEAN_REVERSION, config: Optional[MeanReversionStrategyConfig] = None):
        default_config = MeanReversionStrategyConfig()
        super().__init__(strategy_type, config or default_config)
        self.config = config or default_config
        self.orchestrator: Optional[SignalProcessor] = None

    def initialize(self) -> bool:
        try:
            # config 기반 Detector 동적 생성
            detector_map = {
                "MeanReversionBBSignalDetector": MeanReversionBBSignalDetector,
                "MeanReversionRSISignalDetector": MeanReversionRSISignalDetector,
                "MeanReversionStochSignalDetector": MeanReversionStochSignalDetector,
            }
            detectors = []
            for det_cfg in self.config.detectors:
                cls = detector_map[det_cfg["detector_class"]]
                kwargs = dict(det_cfg)
                kwargs.pop("detector_class")
                detectors.append(cls(**kwargs))
            self.orchestrator = SignalProcessor()
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

            # MeanReversion 특화 점수 조정
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

            logger.debug(f"[mean_reversion] 분석 결과: has_signal={has_signal}, score={score}, buy_score={buy_score}, sell_score={sell_score}, details={signal_result.get('details', [])}")

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