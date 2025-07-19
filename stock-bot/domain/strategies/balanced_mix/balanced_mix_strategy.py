"""
balanced_mix 전략 조합 실행체 (독립 패키지)

- TREND_FOLLOWING(0.5), MEAN_REVERSION(0.5) 전략을 가중치 기반으로 조합
- 각 하위 전략의 analyze 결과(점수, 근거 등)를 가중 평균하여 최종 신호 산출
- 임계값 조정(threshold_adjustment=1.0, 기본 8.0)
- 신호 발생 시 모든 하위 전략의 evidence를 통합하여 반환

사용 예시:
    mix_strategy = BalancedMixStrategy()
    mix_strategy.register_sub_strategies({
        StrategyType.TREND_FOLLOWING: trend_following,
        StrategyType.MEAN_REVERSION: mean_reversion
    })
    result = mix_strategy.analyze(df, ticker, market_trend, long_term_trend)

주요 파라미터:
    - config: BalancedMixConfig (조합 전략, 가중치, 임계값 등)
    - sub_strategies: 하위 전략 객체 딕셔너리

반환값:
    - StrategyResult: 신호 발생 여부, 점수, 신호 근거, 매수/매도 점수 등
"""

from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.models import StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs import BALANCED_MIX_CONFIG, BalancedMixConfig, StrategyMixMode

logger = get_logger(__name__)

class BalancedMixStrategy(BaseStrategy):
    """
    balanced_mix 전략 조합 실행체
    - TREND_FOLLOWING, MEAN_REVERSION 전략을 가중치 기반으로 조합
    - 각 전략의 analyze 결과를 받아 가중 평균, 임계값 조정, 근거 통합 등 수행
    """
    def __init__(self, config: Optional[BalancedMixConfig] = None):
        """
        Args:
            config (BalancedMixConfig, optional): 조합 전략 config. 기본값은 BALANCED_MIX_CONFIG
        """
        super().__init__(StrategyType.BALANCED, config)
        self.config = config or BALANCED_MIX_CONFIG
        self.sub_strategies: Dict[StrategyType, BaseStrategy] = {}
        self.is_initialized = False

    def register_sub_strategies(self, strategies: Dict[StrategyType, BaseStrategy]):
        """
        조합에 사용할 하위 전략 객체들을 등록
        Args:
            strategies (dict): {StrategyType: 전략 인스턴스}
        """
        self.sub_strategies = strategies
        self.is_initialized = True

    def analyze(self,
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Optional[Dict] = None) -> StrategyResult:
        """
        하위 전략들의 analyze 결과를 가중 평균하여 최종 신호 산출
        Args:
            df_with_indicators (pd.DataFrame): 기술적 지표 포함 데이터프레임
            ticker (str): 종목 코드
            market_trend (TrendType): 단기 시장 추세
            long_term_trend (TrendType): 장기 시장 추세
            daily_extra_indicators (dict): 추가 지표
        Returns:
            StrategyResult: 신호 발생 여부, 점수, 근거 등
        """
        if not self.is_initialized:
            raise RuntimeError("BalancedMixStrategy: 하위 전략이 등록되지 않았습니다.")

        individual_results = {}
        for strategy_type, weight in self.config.strategies.items():
            strategy = self.sub_strategies.get(strategy_type)
            if strategy is not None:
                result = strategy.analyze(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
                )
                individual_results[strategy_type] = (result, weight)

        return self._weighted_combination(individual_results)

    def _weighted_combination(self, individual_results: Dict[StrategyType, tuple]) -> StrategyResult:
        """
        가중치 기반 조합 로직 (strategy_manager.py 참고)
        Args:
            individual_results (dict): {StrategyType: (StrategyResult, weight)}
        Returns:
            StrategyResult: 조합된 최종 신호 결과
        """
        total_weighted_buy_score = 0.0
        total_weighted_sell_score = 0.0
        total_weight = 0.0
        all_signals = []
        total_confidence = 0.0
        strategy_names = []

        for strategy_type, (result, weight) in individual_results.items():
            logger.debug(f"[balanced_mix] 하위 전략: {strategy_type}, 점수: (매수 {result.buy_score}, 매도 {result.sell_score}), 가중치: {weight}")
            total_weighted_buy_score += result.buy_score * weight
            total_weighted_sell_score += result.sell_score * weight
            total_weight += weight
            total_confidence += getattr(result, 'confidence', 1.0) * weight
            all_signals.extend(result.signals_detected)
            strategy_names.append(f"{result.strategy_name}({weight:.1f})")

        logger.debug(f"[balanced_mix] 누적 가중합: 매수 {total_weighted_buy_score}, 매도 {total_weighted_sell_score}, 총 가중치: {total_weight}")
        final_buy_score = total_weighted_buy_score / total_weight if total_weight > 0 else 0
        final_sell_score = total_weighted_sell_score / total_weight if total_weight > 0 else 0
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0
        logger.debug(f"[balanced_mix] 최종 가중평균: 매수 {final_buy_score}, 매도 {final_sell_score}, 신뢰도 {final_confidence}")

        # 임계값 조정
        adjusted_threshold = self.config.threshold_adjustment * 8.0  # 기본 임계값 8.0
        logger.debug(f"[balanced_mix] 임계값(조정): {adjusted_threshold}")

        final_score = 0
        has_signal = False
        if final_buy_score > final_sell_score and final_buy_score >= adjusted_threshold:
            final_score = final_buy_score
            has_signal = True
            logger.info(f"[balanced_mix] 매수 신호 발생! (점수: {final_buy_score} >= 임계값: {adjusted_threshold})")
        elif final_sell_score > final_buy_score and final_sell_score >= adjusted_threshold:
            final_score = final_sell_score
            has_signal = True
            logger.info(f"[balanced_mix] 매도 신호 발생! (점수: {final_sell_score} >= 임계값: {adjusted_threshold})")
        else:
            logger.info(f"[balanced_mix] 신호 없음 (매수: {final_buy_score}, 매도: {final_sell_score}, 임계값: {adjusted_threshold})")

        return StrategyResult(
            strategy_name=f"Mix({' + '.join(strategy_names)})",
            strategy_type=StrategyType.BALANCED,
            has_signal=has_signal,
            total_score=final_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=all_signals,
            signal=None,
            confidence=final_confidence,
            buy_score=final_buy_score,
            sell_score=final_sell_score
        ) 