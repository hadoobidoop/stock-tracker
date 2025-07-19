"""
conservative_reversion_hybrid 전략 구현체 (독립 패키지)

- CONSERVATIVE(추세 확인) + MEAN_REVERSION(평균 회귀 진입) 하이브리드 전략
- 보수적 전략으로 큰 추세를 확인한 뒤, 평균 회귀 신호에 따라 진입/청산
- 추세 동의 시 보너스, 반대 시 페널티, 장기추세 가중치 등 적용

사용 예시:
    strategy = ConservativeReversionHybridStrategy(strategy_type, config)
    strategy.initialize()
    result = strategy.analyze(df, ticker, market_trend, long_term_trend, extra_indicators)

주요 파라미터:
    - strategy_type: StrategyType
    - config: StrategyConfig

반환값:
    - StrategyResult: 신호 발생 여부, 점수, 근거, 매수/매도 점수 등
"""

from typing import Dict
import pandas as pd
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.base.models import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.strategies.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy
from domain.strategies.conservative.configs.conservative_config import ConservativeStrategyConfig
from domain.strategies.mean_reversion.configs.mean_reversion_config import MEAN_REVERSION_CONFIG

logger = get_logger(__name__)

class ConservativeReversionHybridStrategy(BaseStrategy):
    """
    Conservative Reversion Hybrid 전략
    - CONSERVATIVE(추세 확인) + MEAN_REVERSION(평균 회귀 진입) 하이브리드
    - 보수적 전략으로 큰 추세를 확인한 뒤, 평균 회귀 신호에 따라 진입/청산
    - 추세 동의 시 보너스, 반대 시 페널티, 장기추세 가중치 등 적용
    """
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        conservative_config = ConservativeStrategyConfig(
            name="Conservative Strategy",
            description="Low-risk conservative trading strategy"
        )
        mean_reversion_config = MEAN_REVERSION_CONFIG
        self.conservative_strategy = ConservativeStrategy(StrategyType.CONSERVATIVE, conservative_config)
        self.mean_reversion_strategy = MeanReversionStrategy(StrategyType.MEAN_REVERSION, mean_reversion_config)

    def initialize(self) -> bool:
        """
        하위 전략 초기화
        Returns:
            bool: 성공 여부
        """
        is_conservative_ok = self.conservative_strategy.initialize()
        is_reversion_ok = self.mean_reversion_strategy.initialize()
        self.is_initialized = is_conservative_ok and is_reversion_ok
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        """
        Returns:
            StrategyType: 전략 타입
        """
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """
        Returns:
            SignalDetectionOrchestrator: 신호 오케스트레이터
        """
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType,
                long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        """
        신호 분석 (추세 확인 + 평균 회귀)
        Args:
            df_with_indicators (pd.DataFrame): 기술적 지표 포함 데이터프레임
            ticker (str): 종목 코드
            market_trend (TrendType): 단기 시장 추세
            long_term_trend (TrendType): 장기 시장 추세
            daily_extra_indicators (dict): 추가 지표
        Returns:
            StrategyResult: 신호 발생 여부, 점수, 근거 등
        Raises:
            RuntimeError: 초기화되지 않은 경우
        """
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        # 1. 하위 전략별 분석
        conservative_result = self.conservative_strategy.analyze(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)
        reversion_result = self.mean_reversion_strategy.analyze(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)

        logger.debug(f"[ConservativeReversionHybrid] {ticker} CONSERVATIVE: buy_score={conservative_result.buy_score}, sell_score={conservative_result.sell_score}, signals={conservative_result.signals_detected}")
        logger.debug(f"[ConservativeReversionHybrid] {ticker} MEAN_REVERSION: buy_score={reversion_result.buy_score}, sell_score={reversion_result.sell_score}, signals={reversion_result.signals_detected}")

        buy_score = reversion_result.buy_score
        sell_score = reversion_result.sell_score

        # 2. 추세 확인 후 진입 로직
        if reversion_result.buy_score > reversion_result.sell_score:
            if conservative_result.buy_score > conservative_result.sell_score:
                logger.debug(f"[ConservativeReversionHybrid] {ticker} 상승 동의: 보수적 전략 buy_score 보너스 적용 (+{conservative_result.buy_score * 0.5:.2f})")
                buy_score += conservative_result.buy_score * 0.5
            else:
                logger.debug(f"[ConservativeReversionHybrid] {ticker} 상승 반대: 보수적 전략 buy_score 페널티 적용 (x0.5)")
                buy_score *= 0.5
        elif reversion_result.sell_score > reversion_result.buy_score:
            if conservative_result.sell_score > conservative_result.buy_score:
                logger.debug(f"[ConservativeReversionHybrid] {ticker} 하락 동의: 보수적 전략 sell_score 보너스 적용 (+{conservative_result.sell_score * 0.5:.2f})")
                sell_score += conservative_result.sell_score * 0.5
            else:
                logger.debug(f"[ConservativeReversionHybrid] {ticker} 하락 반대: 보수적 전략 sell_score 페널티 적용 (x0.5)")
                sell_score *= 0.5

        # 3. 장기추세 가중치 적용
        if long_term_trend == TrendType.BULLISH:
            logger.debug(f"[ConservativeReversionHybrid] {ticker} 장기 BULLISH: buy_score x1.2")
            buy_score *= 1.2
        elif long_term_trend == TrendType.BEARISH:
            logger.debug(f"[ConservativeReversionHybrid] {ticker} 장기 BEARISH: sell_score x1.2")
            sell_score *= 1.2

        # 4. 신호/근거/점수 종합
        final_signals = conservative_result.signals_detected + reversion_result.signals_detected
        stop_loss_price = reversion_result.stop_loss_price

        has_signal = buy_score > self.config.signal_threshold or sell_score > self.config.signal_threshold
        total_score = max(buy_score, sell_score) if has_signal else 0

        logger.info(
            f"[ConservativeReversionHybrid] {ticker} 최종 buy_score={buy_score:.2f}, sell_score={sell_score:.2f}, "
            f"임계값={self.config.signal_threshold}, 신호발생={has_signal}, total_score={total_score:.2f}"
        )

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