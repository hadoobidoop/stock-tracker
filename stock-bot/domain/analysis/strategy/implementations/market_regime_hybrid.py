from typing import Dict

import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.config.static_strategies import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from domain.stock.service.market_data_service import MarketDataService
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketRegimeHybridStrategy(BaseStrategy):
    """
    시장 체제 적응형 하이브리드 전략:
    시장의 추세와 변동성을 진단하여, 최적의 하위 전략을 동적으로 선택합니다.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        from domain.analysis.strategy.strategy_factory import StrategyFactory
        self.trend_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_FOLLOWING)
        self.reversion_strategy = StrategyFactory.create_static_strategy(StrategyType.MEAN_REVERSION)
        self.volatility_strategy = StrategyFactory.create_static_strategy(StrategyType.VOLATILITY_BREAKOUT)
        self.market_data_service = MarketDataService()

    def initialize(self) -> bool:
        self.is_initialized = all([
            self.trend_strategy.initialize(),
            self.reversion_strategy.initialize(),
            self.volatility_strategy.initialize()
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

        # 1. 시장 체제 진단
        current_date = df_with_indicators.index[-1].date()
        vix_value = self.market_data_service.get_vix_by_date(current_date) or 20  # VIX 데이터 없으면 중간값 사용

        is_trending = market_trend != TrendType.NEUTRAL
        is_volatile = vix_value > 25

        # 2. 최적의 하위 전략 선택
        chosen_strategy = None
        regime = "Unknown"
        if is_trending and not is_volatile:  # 안정적 상승장/하락장
            chosen_strategy = self.trend_strategy
            regime = "Trending"
        elif is_trending and is_volatile:  # 변동성 상승장/하락장
            chosen_strategy = self.volatility_strategy
            regime = "Volatile Trending"
        elif not is_trending and is_volatile:  # 추세 없는 변동성장 (하락장의 기술적 반등)
            chosen_strategy = self.reversion_strategy
            regime = "Mean Reversion"
        else:  # 횡보장 (거래 없음)
            regime = "Sideways"
            return StrategyResult(strategy_name=self.get_name(), strategy_type=self.strategy_type, has_signal=False,
                                  total_score=0, buy_score=0, sell_score=0, signals_detected=[], stop_loss_price=None,
                                  signal_strength="", signal=None)

        logger.debug(f"[{current_date}] Market Regime for {ticker}: {regime} (VIX: {vix_value:.2f}) -> Chosen Strategy: {chosen_strategy.get_name()}")

        # 3. 선택된 전략으로 분석 실행
        result = chosen_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend,
                                         daily_extra_indicators)

        # 4. 동적 리스크 관리 (VIX에 따라 점수 조정)
        if vix_value > 30:  # 매우 위험
            result.buy_score *= 0.7
            result.sell_score *= 0.7
        elif vix_value < 15:  # 매우 안정
            result.buy_score *= 1.2
            result.sell_score *= 1.2
            
        # 5. 최종 결과를 이 전략의 이름으로 다시 포장하여 반환
        final_signals = [f"Chosen sub-strategy: {chosen_strategy.get_name()}"] + result.signals_detected
        
        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=result.has_signal,
            total_score=result.total_score,
            buy_score=result.buy_score,
            sell_score=result.sell_score,
            signals_detected=final_signals,
            stop_loss_price=result.stop_loss_price,
            signal_strength=result.signal_strength,
            signal=result.signal
        )
