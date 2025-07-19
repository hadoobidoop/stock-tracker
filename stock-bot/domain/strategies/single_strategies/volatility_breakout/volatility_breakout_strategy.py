# -*- coding: utf-8 -*-
"""
Volatility Breakout 전략 (변동성 돌파)
--------------------------------------
- 완전 독립 패키지 구조(domain/strategies/volatility_breakout/)에서 관리
- Detector, config, 전략 본체가 모두 폴더 내에서 독립적으로 관리됨
- 볼린저밴드(BB) breakout, ADX, 거래량 신호를 조합하여 변동성 응축 후 돌파 구간을 포착
- 각 Detector는 커스텀 래퍼 클래스로 분리되어 유지보수/확장에 용이
- config 분리로 파라미터/가중치 조정이 용이

사용 예시:
    from domain.strategies.single_strategies.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
    strategy = VolatilityBreakoutStrategy(config)
    ...
"""

from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.models import StrategyType
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.models.strategy_result import StrategyResult
from domain.analysis.base.models.base_strategy import BaseStrategy
from domain.strategies.single_strategies.volatility_breakout.detectors.volatility_breakout_adx_detector import \
    VolatilityBreakoutADXDetector
# Volatility Breakout 전략 본체
from domain.strategies.single_strategies.volatility_breakout.detectors.volatility_breakout_bb_detector import VolatilityBreakoutBBDetector
from domain.strategies.single_strategies.volatility_breakout.detectors.volatility_breakout_volume_detector import \
    VolatilityBreakoutVolumeDetector
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout 전략 (볼린저밴드 돌파 + ADX + 거래량)
    - Detector, config 모두 폴더 내에서 독립 관리
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
        self.detectors = [
            VolatilityBreakoutBBDetector(weight=7.0, detector_type="breakout"),
            VolatilityBreakoutADXDetector(weight=4.0),
            VolatilityBreakoutVolumeDetector(weight=5.0),
        ]

    def initialize(self) -> bool:
        try:
            self.orchestrator = SignalDetectionOrchestrator()
            for detector in self.detectors:
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
