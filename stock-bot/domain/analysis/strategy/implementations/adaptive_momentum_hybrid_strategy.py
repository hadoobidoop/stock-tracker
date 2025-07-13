from typing import Dict

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class AdaptiveMomentumStrategy(BaseStrategy):
    """
    적응형 모멘텀 전략: 추세와 모멘텀 전략을 결합하여 신호를 생성합니다.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        # StrategyFactory를 사용하여 내부적으로 다른 전략들을 인스턴스화
        # 순환 참조 방지를 위해 메서드 내에서 import
        from domain.analysis.strategy.strategy_factory import StrategyFactory
        self.trend_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_FOLLOWING)
        self.momentum_strategy = StrategyFactory.create_static_strategy(StrategyType.MOMENTUM)

    def initialize(self) -> bool:
        """하위 전략들을 초기화합니다."""
        is_trend_ok = self.trend_strategy.initialize()
        is_momentum_ok = self.momentum_strategy.initialize()
        self.is_initialized = is_trend_ok and is_momentum_ok
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        # 이 전략은 오케스트레이터를 직접 사용하지 않으므로 빈 것을 반환
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType,
                long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        # 1. 각 내부 전략으로부터 신호 분석
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        trend_result = self.trend_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend,
                                                   daily_extra_indicators)
        momentum_result = self.momentum_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend,
                                                         daily_extra_indicators)

        # 2. 신호 점수 조합 (가중치: 추세 50%, 모멘텀 50%)
        buy_score = (trend_result.buy_score * 0.5) + (momentum_result.buy_score * 0.5)
        sell_score = (trend_result.sell_score * 0.5) + (momentum_result.sell_score * 0.5)

        # === 장기추세 가중치 적용 ===
        if long_term_trend == TrendType.BULLISH:
            buy_score *= 1.2
        elif long_term_trend == TrendType.BEARISH:
            sell_score *= 1.2
        # ============================

        # 3. 최종 결과 생성
        final_signals = trend_result.signals_detected + momentum_result.signals_detected

        # 두 전략의 정지 손절 가격 중 더 보수적인(안전한) 값을 선택
        stop_loss_price = None
        if trend_result.stop_loss_price and momentum_result.stop_loss_price:
            if buy_score > sell_score:  # 매수 신호일 경우 더 낮은 값
                stop_loss_price = min(trend_result.stop_loss_price, momentum_result.stop_loss_price)
            else:  # 매도 신호일 경우 더 높은 값
                stop_loss_price = max(trend_result.stop_loss_price, momentum_result.stop_loss_price)
        elif trend_result.stop_loss_price:
            stop_loss_price = trend_result.stop_loss_price
        else:
            stop_loss_price = momentum_result.stop_loss_price

        # 4. StrategyResult 객체 직접 생성 (오류 수정)
        has_signal = buy_score > self.config.signal_threshold or sell_score > self.config.signal_threshold
        total_score = 0
        if has_signal:
            total_score = buy_score if buy_score > sell_score else sell_score

        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=has_signal,
            total_score=total_score,
            buy_score=buy_score,
            sell_score=sell_score,
            signals_detected=final_signals,
            stop_loss_price=stop_loss_price,
            signal_strength="",  # dataclass에서 자동 계산
            signal=None  # 필요 시 생성 로직 추가
        )
