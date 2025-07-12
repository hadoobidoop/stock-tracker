from typing import Dict

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.config.static_strategies import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class ConservativeReversionHybridStrategy(BaseStrategy):
    """
    보수적 평균 회귀 하이브리드 전략:
    - CONSERVATIVE 전략으로 큰 추세를 확인합니다.
    - MEAN_REVERSION 전략으로 추세 내의 진입 시점을 포착합니다.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        from domain.analysis.strategy.strategy_factory import StrategyFactory
        self.conservative_strategy = StrategyFactory.create_static_strategy(StrategyType.CONSERVATIVE)
        self.mean_reversion_strategy = StrategyFactory.create_static_strategy(StrategyType.MEAN_REVERSION)

    def initialize(self) -> bool:
        is_conservative_ok = self.conservative_strategy.initialize()
        is_reversion_ok = self.mean_reversion_strategy.initialize()
        self.is_initialized = is_conservative_ok and is_reversion_ok
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
        reversion_result = self.mean_reversion_strategy.analyze(df_with_indicators, ticker, market_trend,
                                                                long_term_trend, daily_extra_indicators)

        buy_score = reversion_result.buy_score
        sell_score = reversion_result.sell_score

        # "추세 확인 후 진입" 로직
        # 1. 평균 회귀가 매수 신호를 보냈을 때
        if reversion_result.buy_score > reversion_result.sell_score:
            # 보수적 전략도 상승 추세에 동의하면 보너스 점수
            if conservative_result.buy_score > conservative_result.sell_score:
                buy_score += conservative_result.buy_score * 0.5  # 추세 점수의 50%를 보너스로
            # 추세가 반대이면 페널티
            else:
                buy_score *= 0.5

        # 2. 평균 회귀가 매도 신호를 보냈을 때
        elif reversion_result.sell_score > reversion_result.buy_score:
            # 보수적 전략도 하락 추세에 동의하면 보너스 점수
            if conservative_result.sell_score > conservative_result.buy_score:
                sell_score += conservative_result.sell_score * 0.5
            # 추세가 반대이면 페널티
            else:
                sell_score *= 0.5

        final_signals = conservative_result.signals_detected + reversion_result.signals_detected
        stop_loss_price = reversion_result.stop_loss_price

        has_signal = buy_score > self.config.signal_threshold or sell_score > self.config.signal_threshold
        total_score = max(buy_score, sell_score) if has_signal else 0

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
