# -*- coding: utf-8 -*-
"""
Momentum 전략 구현체
- 커스텀/기본 Detector(RSI, Stoch, MACD, Volume, Composite) 조합
- 신호/점수/근거/로깅/쿨다운/예외처리 등 robust하게 구현
- 설계 의도: 모멘텀 신호 중심, 신호 빈도와 신뢰도 균형

사용법:
    config = MomentumStrategyConfig()
    strategy = MomentumStrategy(StrategyType.MOMENTUM, config)
    strategy.initialize()
    result = strategy.analyze(df, ticker, market_trend, long_term_trend)

주요 튜닝 포인트:
    - signal_threshold: 신호 발생 기준점(기본 6.0)
    - detector_weights: 각 Detector별 가중치(RSI > Stoch > MACD > Volume > Composite)
    - score_multiplier: 점수 조정(기본 1.0)
    - max_positions/position_hold_hours: 포지션 관리(4개/24시간)
"""
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from domain.signals.models.enums import StrategyType
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector
from domain.signals.models.strategy_result import StrategyResult
from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.strategies.single.momentum.configs.momentum_config import MomentumStrategyConfig
from domain.strategies.single.momentum.detectors.momentum_rsi_detector import RSISignalDetector
from domain.strategies.single.momentum.detectors.momentum_rsi_stoch_detector import RSIStochDetector
from domain.strategies.single.momentum.detectors.momentum_stoch_detector import StochSignalDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.strategies.base import BaseStrategy

logger = get_logger(__name__)

class MomentumStrategy(BaseStrategy):
    """
    RSI, Stoch 등 모멘텀 지표를 중심으로 신호를 감지하는 전략
    - 커스텀/기본 Detector 조합, Composite(RSI+Stoch) 컨펌
    - 신호/점수/근거/로깅/쿨다운/예외처리 robust
    - 설계 의도: 신호 빈도와 신뢰도의 균형
    """
    def __init__(self, strategy_type: StrategyType, config: MomentumStrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalProcessor] = None
        self.config = config

    def initialize(self) -> bool:
        """
        Detector 조합 및 orchestrator 초기화
        - 커스텀/기본 Detector: RSISignalDetector, StochSignalDetector, MACDSignalDetector, VolumeSignalDetector
        - Composite Detector: RSI+Stoch 컨펌(신호 신뢰도 강화)
        - Detector별 가중치는 config.detector_weights에서 관리
        """
        try:
            detectors = [
                RSISignalDetector(weight=self.config.detector_weights['rsi']),
                StochSignalDetector(weight=self.config.detector_weights['stoch']),
                MACDSignalDetector(weight=self.config.detector_weights['macd']),
                VolumeSignalDetector(weight=self.config.detector_weights['volume']),
                RSIStochDetector(
                    weight=self.config.detector_weights['composite']
                )
            ]
            self.orchestrator = SignalProcessor()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (커스텀/기본 Detector 사용)")
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
        신호 분석 및 결과 반환
        - 쿨다운 체크, orchestrator 기반 신호/점수/근거 수집
        - market_trend, long_term_trend에 따라 점수 가중치 조정
        - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
        - 예외 발생 시 안전하게 실패 반환
        """
        current_time = datetime.now()
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
            # Momentum 특화 점수 조정
            original_score = score
            if market_trend == TrendType.BULLISH:
                score *= self.config.long_term_bullish_multiplier
            elif market_trend == TrendType.BEARISH:
                score *= self.config.long_term_bearish_multiplier
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
            buy_score = signal_result.get('buy_score', 0.0)
            sell_score = signal_result.get('sell_score', 0.0)
            # === 장기추세 가중치 적용 ===
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