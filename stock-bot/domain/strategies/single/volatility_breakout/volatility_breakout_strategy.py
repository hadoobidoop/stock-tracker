# -*- coding: utf-8 -*-
"""
Volatility Breakout 전략 (변동성 돌파)
--------------------------------------
- 중앙 Detector(BB, ADX, Volume) + 파라미터 주입 방식
- 볼린저밴드(BB) breakout, ADX, 거래량 신호를 조합하여 변동성 응축 후 돌파 구간을 포착
- 각 Detector는 중앙 detector를 사용하여 일관성 있게 관리
- config 분리로 파라미터/가중치 조정이 용이

사용 예시:
    from domain.strategies.single.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
    strategy = VolatilityBreakoutStrategy(config)
    ...
"""

from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.detectors.trend_following.adx_detector import ADXSignalDetector
from domain.signals.detectors.volatility.bb_detector import BBSignalDetector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout 전략 (볼린저밴드 돌파 + ADX + 거래량)
    - 중앙 Detector + 파라미터 주입 방식
    - 변동성 응축(squeeze) 후 상단/하단 돌파 및 거래량 급증 구간을 포착
    - 각 Detector별 신호 근거(TechnicalIndicatorEvidence)를 상세 기록
    """
    def __init__(self, strategy_type: StrategyType = StrategyType.VOLATILITY_BREAKOUT, config=None):
        """
        Volatility Breakout 전략 인스턴스 생성
        :param strategy_type: 전략 타입
        :param config: Detector 가중치, 파라미터 등 설정(dict 또는 config 객체)
        """
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalProcessor] = None

    def initialize(self) -> bool:
        try:
            # VolatilityBreakout 전략용 파라미터 설정
            volatility_breakout_bb_params = {
                'detector_type': 'breakout',  # breakout 모드
                'bb_period': 20,
                'bb_std': 2.0,
                'breakout_threshold': 0.05,  # 돌파 임계값
                'squeeze_confirmation_required': True  # 응축 확인 필요
            }
            
            volatility_breakout_adx_params = {
                'adx_threshold': 25,  # 기본 25 유지
                'trend_strength_required': True,  # 추세 강도 확인 필요
                'breakout_mode': True  # 돌파 모드 활성화
            }
            
            volatility_breakout_volume_params = {
                'volume_threshold': 1.5,  # 기본 2.0에서 더 낮게
                'breakout_confirmation_required': True  # 돌파 확인 필요
            }
            
            detectors = [
                BBSignalDetector(
                    weight=7.0,
                    name="VolatilityBreakout_BB_Detector",
                    parameters=volatility_breakout_bb_params
                ),
                ADXSignalDetector(
                    weight=4.0,
                    name="VolatilityBreakout_ADX_Detector",
                    parameters=volatility_breakout_adx_params
                ),
                VolumeSignalDetector(
                    weight=5.0,
                    name="VolatilityBreakout_Volume_Detector",
                    parameters=volatility_breakout_volume_params
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

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

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
