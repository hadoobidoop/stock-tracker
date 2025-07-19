# -*- coding: utf-8 -*-
"""
SCALPING 전략 (독립 패키지)

- 초단기(4시간 이내) 매매를 위한 스캘핑 전략
- 주요 Detector: RSI, Stoch, Volume, MACD (가중치 조합)
- VIX(변동성지수) 기반 점수 조정(25 초과: 1.2배, 15 미만: 0.8배)
- 빠른 진입/청산, 거래량 신호, 변동성 필터에 중점
- 전략 파라미터, 신호 근거, 포지션 관리 등은 config에서 관리

사용 예시:
    config = ScalpingStrategyConfig()
    strategy = ScalpingStrategy(StrategyType.SCALPING, config)
    strategy.initialize()
    result = strategy.analyze(df, ticker, market_trend, long_term_trend)

주요 파라미터:
    - signal_threshold: 신호 발생 기준점(기본 4.0)
    - detector_weights: 각 Detector별 가중치(RSI, Stoch, Volume, MACD)
    - max_positions/position_hold_hours: 포지션 관리(10개/4시간)
    - vix_high_multiplier/vix_low_multiplier: VIX 점수 조정 배수

반환값:
    - StrategyResult: 신호 발생 여부, 점수, 신호 근거, 매수/매도 점수 등
"""

from typing import Dict, Optional

import pandas as pd

from domain.analysis.config.signals.service.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.models.base_strategy import BaseStrategy
from domain.strategies.strategy_config import StrategyConfig
from domain.analysis.models.enums import StrategyType
from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector
from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
from domain.analysis.models.strategy_result import StrategyResult
from domain.stock.service.market_data_service import MarketDataService
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ScalpingStrategy(BaseStrategy):
    """
    SCALPING(스캘핑) 전략 구현체
    - 초단기(4시간 이내) 매매, 빠른 진입/청산
    - RSI, Stoch, Volume, MACD Detector 가중치 조합
    - VIX(변동성지수) 기반 점수 조정
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        """
        Args:
            strategy_type (StrategyType): 전략 타입 (SCALPING)
            config (StrategyConfig): 전략 설정(config)
        """
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None
        self.market_data_service = MarketDataService()  # VIX 등 외부 마켓 데이터 활용

    def initialize(self) -> bool:
        """
        Detector 조합 및 오케스트레이터 초기화
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            detectors = [
                RSISignalDetector(weight=4.0),
                StochSignalDetector(weight=4.0),
                VolumeSignalDetector(weight=5.0),
                MACDSignalDetector(weight=3.0)
            ]
            self.orchestrator = SignalDetectionOrchestrator()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (Detector 조합: RSI, Stoch, Volume, MACD)")
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
        신호 분석 및 점수 산출
        Args:
            df_with_indicators (pd.DataFrame): 기술적 지표 포함 데이터프레임
            ticker (str): 종목 코드
            market_trend (TrendType): 단기 시장 추세
            long_term_trend (TrendType): 장기 시장 추세
            daily_extra_indicators (dict): 추가 지표
        Returns:
            StrategyResult: 신호 발생 여부, 점수, 근거 등
        """
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")

        self.last_analysis_time = pd.Timestamp.now(tz='UTC')

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

            # VIX 기반 점수 조정 (25 초과: 1.2배, 15 미만: 0.8배)
            current_date = df_with_indicators.index[-1].date()
            vix_value = self.market_data_service.get_vix_by_date(current_date)
            if vix_value is not None:
                if vix_value > 25:
                    score *= 1.2
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) > 25. Score adjusted by 1.2x.")
                elif vix_value < 15:
                    score *= 0.8
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) < 15. Score adjusted by 0.8x.")
            else:
                logger.warning(f"SCALPING: VIX data not available for {current_date}. No adjustment made.")

            # 성능 지표 업데이트 (최근 100개 평균)
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