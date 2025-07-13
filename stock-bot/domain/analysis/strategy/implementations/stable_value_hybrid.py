from typing import Dict

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StableValueHybridStrategy(BaseStrategy):
    """
    안정 가치 하이브리드 전략:
    - CONSERVATIVE 전략으로 시장의 안정적인 상승 추세를 확인합니다.
    - TREND_PULLBACK 전략으로 추세 내의 눌림목 매수 시점을 포착합니다.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        from domain.analysis.strategy.strategy_factory import StrategyFactory
        self.conservative_strategy = StrategyFactory.create_static_strategy(StrategyType.CONSERVATIVE)
        self.pullback_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_PULLBACK)

    def initialize(self) -> bool:
        self.is_initialized = all([
            self.conservative_strategy.initialize(),
            self.pullback_strategy.initialize()
        ])
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType,
                long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        conservative_result = self.conservative_strategy.analyze(df_with_indicators, ticker, market_trend,
                                                                 long_term_trend, daily_extra_indicators)
        pullback_result = self.pullback_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend,
                                                         daily_extra_indicators)

        buy_score = 0
        sell_score = 0  # 이 전략은 매수만 고려

        # CONSERVATIVE 전략이 안정적인 상승 추세라고 판단할 때만,
        # TREND_PULLBACK의 눌림목 매수 신호를 채택
        if conservative_result.buy_score > conservative_result.sell_score:
            buy_score = pullback_result.buy_score

        final_signals = conservative_result.signals_detected + pullback_result.signals_detected
        stop_loss_price = pullback_result.stop_loss_price

        has_signal = buy_score > self.config.signal_threshold
        total_score = buy_score if has_signal else 0

        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=has_signal,
            total_score=total_score,
            buy_score=buy_score,
            sell_score=sell_score,
            signals_detected=final_signals,
            stop_loss_price=stop_loss_price,
            signal_strength="",
            signal=None
        )
