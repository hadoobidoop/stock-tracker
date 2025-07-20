# MultiTimeframeStrategy (다중 시간대 전략)
# ======================================
# - 장기(일봉)와 단기(시간봉) 신호를 동시에 확인하여 신뢰도 높은 진입/청산 신호를 포착하는 전략
# - 중앙 Detector(MACD, Stoch, RSI) + 파라미터 주입 방식
# - 모든 전략 파라미터(config)는 configs/multi_timeframe_config.py에서 관리하며, Detector 가중치·임계값·포지션 관리 등 확장/튜닝이 용이함
# - 각 Detector는 중앙 detector를 사용하여 일관성 있게 관리
# - 확장 포인트: detectors/ 하위에 커스텀 Detector 추가, config에서 동적 조합, 신호 컨펌/복합 판단 로직(CompositeDetector 등) 확장 가능
#
# [주요 파라미터(config)]
#   - signal_threshold: 신호 발생 임계값(9.0)
#   - risk_per_trade: 거래당 리스크 비율(0.02)
#   - detector_weights: Detector 가중치
#   - market_filters: 다중 시간대 컨펌 여부
#   - position_management: 최대 3개 포지션, 21일(504시간) 보유
#
# [사용 예시]
#   from domain.strategies.multi_timeframe.multi_timeframe_strategy import MultiTimeframeStrategy
#   strategy = MultiTimeframeStrategy()
#   strategy.initialize()
#   result = strategy.analyze(df, ticker, market_trend, long_term_trend, daily_extra_indicators)
#
# [확장/유지보수 포인트]
#   - detectors/ 하위에 커스텀 Detector 추가 및 config에서 동적 조합 가능
#   - 신호 컨펌/복합 판단 로직(CompositeDetector 등) 확장 가능
#   - config 파라미터만 수정해 전략 튜닝 가능

from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector
from domain.signals.detectors.momentum.stoch_detector import StochSignalDetector
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.multi_timeframe_config import MULTI_TIMEFRAME_CONFIG

logger = get_logger(__name__)

class MultiTimeframeStrategy(BaseStrategy):
    """
    [다중 시간대 전략]
    - 장기(일봉)와 단기(시간봉) 신호를 동시에 확인하여 신뢰도 높은 진입/청산 신호를 포착
    - 중앙 Detector(MACD, Stoch, RSI) + 파라미터 주입 방식
    - 모든 파라미터/가중치는 configs/multi_timeframe_config.py에서 관리
    - 확장: detectors/ 하위에 커스텀 Detector 추가, config에서 동적 조합, 신호 컨펌/복합 판단 로직 확장 가능
    """
    def __init__(self, strategy_type: StrategyType = StrategyType.MULTI_TIMEFRAME, config=None):
        """
        MultiTimeframeStrategy 생성자
        Args:
            strategy_type: 전략 타입
            config (dict, optional): 전략 파라미터(config). 미지정 시 기본값(MULTI_TIMEFRAME_CONFIG) 사용
        """
        config = config or MULTI_TIMEFRAME_CONFIG
        super().__init__(strategy_type, config)
        self.config = config
        self.orchestrator: Optional[SignalProcessor] = None

    def initialize(self) -> bool:
        """
        중앙 Detector 조합 및 orchestrator 초기화
        - 중앙 Detector(MACDSignalDetector, StochSignalDetector, RSISignalDetector) 조합
        - 파라미터 주입: 전략별 특화 설정 적용
        - 각 Detector의 가중치는 config["detector_weights"]에서 관리
        Returns:
            bool: 초기화 성공 여부
        Raises:
            Exception: Detector/Orchestrator 생성 실패 시 False 반환 및 로그 기록
        """
        try:
            # MultiTimeframe 전략용 파라미터 설정
            multi_timeframe_macd_params = {
                'signal_sensitivity': 1.0,  # 기본 1.0 유지
                'multi_timeframe_confirmation_required': True  # 다중 시간대 확인 필요
            }
            
            multi_timeframe_stoch_params = {
                'oversold_threshold': 25,  # 기본 25 유지
                'overbought_threshold': 75,  # 기본 75 유지
                'multi_timeframe_confirmation_required': True  # 다중 시간대 확인 필요
            }
            
            multi_timeframe_rsi_params = {
                'oversold_threshold': 35,  # 기본 35 유지
                'overbought_threshold': 65,  # 기본 65 유지
                'multi_timeframe_confirmation_required': True  # 다중 시간대 확인 필요
            }
            
            detectors = [
                MACDSignalDetector(
                    weight=self.config["detector_weights"].get("macd", 3.0),
                    name="MultiTimeframe_MACD_Detector",
                    parameters=multi_timeframe_macd_params
                ),
                StochSignalDetector(
                    weight=self.config["detector_weights"].get("stoch", 3.0),
                    name="MultiTimeframe_Stoch_Detector",
                    parameters=multi_timeframe_stoch_params
                ),
                RSISignalDetector(
                    weight=self.config["detector_weights"].get("rsi", 3.0),
                    name="MultiTimeframe_RSI_Detector",
                    parameters=multi_timeframe_rsi_params
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
        """
        신호 분석 및 결과 반환
        Args:
            df_with_indicators (pd.DataFrame): 시간봉 데이터 및 기술적 지표
            ticker (str): 종목 티커
            market_trend (TrendType): 시장 추세
            long_term_trend (TrendType): 장기 추세
            daily_extra_indicators (dict, optional): 일봉 등 추가 지표
        Returns:
            StrategyResult: 분석 결과(신호, 점수, 근거 등)
        Raises:
            RuntimeError: 초기화 미완료 시 예외 발생
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