# -*- coding: utf-8 -*-
"""
Aggressive 전략 구현체
- 중앙 Detector를 파라미터 주입 방식으로 사용
- 민감한 신호 감지 및 점수 조정
"""

from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
# 중앙 Detector import
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector
from domain.signals.detectors.momentum.stoch_detector import StochSignalDetector
from domain.signals.detectors.trend_following.adx_detector import ADXSignalDetector
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.aggressive_config import AggressiveStrategyConfig

logger = get_logger(__name__)


class AggressiveStrategy(BaseStrategy):
    """
    공격적인 신호를 적극적으로 포착하는 전략.
    중앙 Detector를 파라미터 주입 방식으로 사용하여 민감한 신호 감지.
    """

    def __init__(self, strategy_type: StrategyType, config: AggressiveStrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalProcessor] = None
        self.config = config  # AggressiveStrategyConfig로 타입 지정

    def initialize(self) -> bool:
        try:
            # 공격적 전략용 파라미터들
            aggressive_sma_params = {
                'adx_threshold': 15,  # 더 낮은 임계값 (기본 20 → 15)
                'continuation_weight': 0.6,  # 더 높은 지속 가중치 (기본 0.4 → 0.6)
                'trend_confirmation_required': False  # 추세 확인 불필요
            }
            
            aggressive_volume_params = {
                'volume_surge_factor': 1.3,  # 더 낮은 임계값 (기본 1.5 → 1.3)
                'trend_continuation_weight': 0.7,  # 더 높은 지속 가중치 (기본 0.5 → 0.7)
                'min_trend_days': 2  # 더 짧은 확인 기간 (기본 3 → 2)
            }
            
            aggressive_rsi_params = {
                'oversold_threshold': 40,  # 더 높은 임계값 (기본 35 → 40)
                'overbought_threshold': 65,  # 더 낮은 임계값 (기본 70 → 65)
                'exit_bonus_multiplier': 1.5  # 더 높은 보너스 (기본 1.2 → 1.5)
            }
            
            aggressive_adx_params = {
                'adx_strong_threshold': 20,  # 더 낮은 임계값 (기본 25 → 20)
                'adx_weak_threshold': 15,   # 더 낮은 임계값 (기본 20 → 15)
                'weak_trend_multiplier': 0.8  # 더 높은 가중치 (기본 0.5 → 0.8)
            }
            
            # 중앙 Detector들을 파라미터와 함께 생성
            detectors = [
                SMASignalDetector(
                    weight=self.config.detector_weights['sma'],
                    name="Aggressive_SMA_Detector",
                    parameters=aggressive_sma_params
                ),
                MACDSignalDetector(weight=self.config.detector_weights['macd']),
                RSISignalDetector(
                    weight=self.config.detector_weights['rsi'],
                    name="Aggressive_RSI_Detector", 
                    parameters=aggressive_rsi_params
                ),
                StochSignalDetector(weight=self.config.detector_weights['stoch']),
                VolumeSignalDetector(
                    weight=self.config.detector_weights['volume'],
                    name="Aggressive_Volume_Detector",
                    parameters=aggressive_volume_params
                ),
                ADXSignalDetector(
                    weight=self.config.detector_weights['adx'],
                    name="Aggressive_ADX_Detector",
                    parameters=aggressive_adx_params
                )
            ]
            self.orchestrator = SignalProcessor()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (중앙 Detector 파라미터 주입 방식 사용)")
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
        # 쿨다운 체크
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

            # Aggressive 특화 점수 조정
            original_score = score
            score *= self.config.score_multiplier  # 1.2배

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
                signal_strength="ERROR",
                signals_detected=[],
                signal=None,
                buy_score=0.0,
                sell_score=0.0,
                stop_loss_price=None
            )
