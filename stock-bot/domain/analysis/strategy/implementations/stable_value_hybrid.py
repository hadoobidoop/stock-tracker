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
        # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체

    def initialize(self) -> bool:
        self.is_initialized = all([
            self.conservative_strategy.initialize(),
            # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체
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
        # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체

        buy_score = 0
        sell_score = 0  # 이 전략은 매수만 고려

        # CONSERVATIVE 전략이 안정적인 상승 추세라고 판단할 때만,
        # TREND_PULLBACK의 눌림목 매수 신호를 채택
        if conservative_result.buy_score > conservative_result.sell_score:
            buy_score = conservative_result.buy_score # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체

        # === 장기추세 가중치 적용 ===
        if long_term_trend == TrendType.BULLISH:
            buy_score *= 1.2
        elif long_term_trend == TrendType.BEARISH:
            sell_score *= 1.2
        # ============================

        final_signals = conservative_result.signals_detected + conservative_result.signals_detected # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체
        stop_loss_price = conservative_result.stop_loss_price # TREND_PULLBACK 관련 주석, 변수, 생성, 호출 등 삭제 또는 대체

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
