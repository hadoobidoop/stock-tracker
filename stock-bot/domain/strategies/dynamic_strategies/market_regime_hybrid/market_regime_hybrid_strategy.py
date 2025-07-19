from typing import Dict

import pandas as pd

from domain.analysis.models.strategy_result import StrategyResult
from domain.analysis.base.models.base_strategy import BaseStrategy
from domain.analysis.base.models import StrategyConfig, StrategyType
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.stock.service.market_data_service import MarketDataService
from domain.strategies.single_strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy
from domain.strategies.single_strategies.trend_following.trend_following_strategy import TrendFollowingStrategy
from domain.strategies.single_strategies.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.market_regime_hybrid_config import (
    VIX_VOLATILE_THRESHOLD, VIX_HIGH_RISK_THRESHOLD, VIX_LOW_RISK_THRESHOLD,
    VIX_HIGH_RISK_MULTIPLIER, VIX_LOW_RISK_MULTIPLIER, BULLISH_BONUS, BEARISH_BONUS
)

logger = get_logger(__name__)


class MarketRegimeHybridStrategy(BaseStrategy):
    """
    시장 체제 적응형 하이브리드 전략
    --------------------------------
    - 시장의 추세(market_trend)와 변동성(VIX)을 진단하여, 상황에 따라 하위 전략(추세추종, 평균회귀, 변동성돌파) 중 하나를 동적으로 선택해 신호를 생성합니다.
    - 하위 전략은 직접 import하여 인스턴스화하며, 각 전략은 완전히 독립된 패키지 구조를 따릅니다.
    - VIX 임계값, 점수 조정 배수, 장기추세 가중치 등은 configs/market_regime_hybrid_config.py에서 관리합니다.
    - 신호 분석, 점수 조정, 신호 근거 등은 상세 로그로 기록되어 백테스팅/실시간 분석에 활용됩니다.
    """

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        """
        하위 전략(TrendFollowing, MeanReversion, VolatilityBreakout)을 직접 참조하여 인스턴스화
        - 각 하위 전략은 동일한 config를 공유하나, 필요시 별도 config로 확장 가능
        - MarketDataService를 통해 VIX 등 시장 데이터 활용
        """
        super().__init__(strategy_type, config)
        self.trend_strategy = TrendFollowingStrategy(StrategyType.TREND_FOLLOWING, config)
        self.reversion_strategy = MeanReversionStrategy(StrategyType.MEAN_REVERSION, config)
        self.volatility_strategy = VolatilityBreakoutStrategy(StrategyType.VOLATILITY_BREAKOUT, config)
        self.market_data_service = MarketDataService()

    def initialize(self) -> bool:
        """
        모든 하위 전략을 초기화합니다. (하나라도 실패 시 False)
        """
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
        """
        1. 시장 체제 진단: VIX, market_trend로 시장 상황(추세/변동성) 분류
        2. 상황에 따라 하위 전략 중 하나를 선택
        3. 선택된 하위 전략의 analyze() 실행
        4. VIX/장기추세에 따라 buy/sell 점수 동적 조정
        5. 신호 근거에 선택된 하위 전략명을 추가하여 결과 반환
        """
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        logger.debug(f"[MarketRegimeHybrid] 분석 시작 | ticker={ticker} | market_trend={market_trend} | long_term_trend={long_term_trend} | VIX={vix_value}")

        # 1. 시장 체제 진단 (VIX, market_trend)
        current_date = df_with_indicators.index[-1].date()
        vix_value = self.market_data_service.get_vix_by_date(current_date) or 20  # VIX 데이터 없으면 중간값 사용

        is_trending = market_trend != TrendType.NEUTRAL
        is_volatile = vix_value > VIX_VOLATILE_THRESHOLD

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

        # 4. 동적 리스크 관리 (VIX/장기추세에 따라 점수 조정)
        if vix_value > VIX_HIGH_RISK_THRESHOLD:  # 매우 위험
            result.buy_score *= VIX_HIGH_RISK_MULTIPLIER
            result.sell_score *= VIX_HIGH_RISK_MULTIPLIER
        elif vix_value < VIX_LOW_RISK_THRESHOLD:  # 매우 안정
            result.buy_score *= VIX_LOW_RISK_MULTIPLIER
            result.sell_score *= VIX_LOW_RISK_MULTIPLIER
            
        if long_term_trend == TrendType.BULLISH:
            result.buy_score *= BULLISH_BONUS
        elif long_term_trend == TrendType.BEARISH:
            result.sell_score *= BEARISH_BONUS

        # 5. 최종 결과를 이 전략의 이름으로 다시 포장하여 반환
        final_signals = [f"Chosen sub-strategy: {chosen_strategy.get_name()}"] + result.signals_detected
        
        logger.info(
            f"[MarketRegimeHybrid] 결과 | ticker={ticker} | regime={regime} | vix={vix_value:.2f} | has_signal={result.has_signal} | "
            f"buy_score={result.buy_score:.2f} | sell_score={result.sell_score:.2f} | signal_details={result.signals_detected}"
        )

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