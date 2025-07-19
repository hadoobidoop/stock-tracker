"""
conservative_mix 전략 조합 실행체 (독립 패키지)

- CONSERVATIVE, SWING 전략을 투표 기반(과반수 동의)으로 조합
- 각 하위 전략의 analyze 결과(점수, 근거 등)를 투표 방식으로 최종 신호 산출
- 임계값 조정(threshold_adjustment=1.2, 기본 8.0 → 9.6)
- 신호 발생 시 동의한 하위 전략의 evidence만 통합하여 반환

사용 예시:
    mix_strategy = ConservativeMixStrategy()
    mix_strategy.register_sub_strategies({
        StrategyType.CONSERVATIVE: conservative,
        StrategyType.SWING: swing
    })
    result = mix_strategy.analyze(df, ticker, market_trend, long_term_trend)

주요 파라미터:
    - config: ConservativeMixConfig (조합 전략, 임계값 등)
    - sub_strategies: 하위 전략 객체 딕셔너리

반환값:
    - StrategyResult: 신호 발생 여부, 점수, 신호 근거, 매수/매도 점수 등

활용 포인트:
    - 매우 보수적이고 신뢰도 높은 신호만 생성
    - 거짓 신호(false signal) 최소화, 안정적 거래
    - 각 전략별 근거가 모두 기록되어 설명력/디버깅에 유리
"""

from typing import Dict, Optional

import pandas as pd

from domain.analysis.base.models import StrategyType
from domain.analysis.models.strategy_result import StrategyResult
from domain.analysis.base.models.base_strategy import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs import CONSERVATIVE_MIX_CONFIG, ConservativeMixConfig

logger = get_logger(__name__)

class ConservativeMixStrategy(BaseStrategy):
    """
    conservative_mix 전략 조합 실행체
    - CONSERVATIVE, SWING 전략을 투표 기반(과반수 동의)으로 조합
    - 각 전략의 analyze 결과를 받아 투표, 임계값 조정, 근거 통합 등 수행
    """
    def __init__(self, config: Optional[ConservativeMixConfig] = None):
        super().__init__(StrategyType.CONSERVATIVE, config)
        self.config = config or CONSERVATIVE_MIX_CONFIG
        self.sub_strategies: Dict[StrategyType, BaseStrategy] = {}
        self.is_initialized = False

    def register_sub_strategies(self, strategies: Dict[StrategyType, BaseStrategy]):
        self.sub_strategies = strategies
        self.is_initialized = True

    def analyze(self,
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Optional[Dict] = None) -> StrategyResult:
        if not self.is_initialized:
            raise RuntimeError("ConservativeMixStrategy: 하위 전략이 등록되지 않았습니다.")

        individual_results = {}
        for strategy_type in self.config.strategies.keys():
            strategy = self.sub_strategies.get(strategy_type)
            if strategy is not None:
                result = strategy.analyze(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
                )
                individual_results[strategy_type] = result

        return self._voting_combination(individual_results)

    def _voting_combination(self, individual_results: Dict[StrategyType, StrategyResult]) -> StrategyResult:
        """
        투표 기반 조합 로직 (과반수 동의 시 신호 발생)
        Args:
            individual_results (dict): {StrategyType: StrategyResult}
        Returns:
            StrategyResult: 조합된 최종 신호 결과
        """
        votes_buy = 0
        votes_sell = 0
        buy_scores = []
        sell_scores = []
        evidences = []
        strategy_names = []
        confidence_sum = 0.0
        threshold = self.config.threshold_adjustment * 8.0
        logger.debug(f"[conservative_mix] 투표 조합 시작 (임계값: {threshold})")
        for strategy_type, result in individual_results.items():
            logger.debug(f"[conservative_mix] 전략: {result.strategy_name}, 매수점수: {result.buy_score}, 매도점수: {result.sell_score}, 근거: {result.signals_detected}")
            if result.buy_score >= threshold:
                votes_buy += 1
                buy_scores.append(result.buy_score)
                evidences.extend(result.signals_detected)
                strategy_names.append(result.strategy_name)
                confidence_sum += getattr(result, 'confidence', 1.0)
                logger.debug(f"[conservative_mix] → 매수 투표 (점수: {result.buy_score} >= {threshold})")
            elif result.sell_score >= threshold:
                votes_sell += 1
                sell_scores.append(result.sell_score)
                evidences.extend(result.signals_detected)
                strategy_names.append(result.strategy_name)
                confidence_sum += getattr(result, 'confidence', 1.0)
                logger.debug(f"[conservative_mix] → 매도 투표 (점수: {result.sell_score} >= {threshold})")
            else:
                logger.debug(f"[conservative_mix] → 신호 미충족 (매수: {result.buy_score}, 매도: {result.sell_score}, 임계값: {threshold})")

        total_votes = len(individual_results)
        has_signal = False
        final_score = 0
        final_confidence = 0.0
        final_buy_score = max(buy_scores) if buy_scores else 0.0
        final_sell_score = max(sell_scores) if sell_scores else 0.0
        logger.debug(f"[conservative_mix] 매수 득표: {votes_buy}, 매도 득표: {votes_sell}, 전체 전략: {total_votes}")
        if votes_buy > total_votes / 2:
            has_signal = True
            final_score = final_buy_score
            final_confidence = confidence_sum / votes_buy if votes_buy else 0.0
            logger.debug(f"[conservative_mix] 최종 신호: 매수 (득표: {votes_buy}/{total_votes}, 점수: {final_score})")
        elif votes_sell > total_votes / 2:
            has_signal = True
            final_score = final_sell_score
            final_confidence = confidence_sum / votes_sell if votes_sell else 0.0
            logger.debug(f"[conservative_mix] 최종 신호: 매도 (득표: {votes_sell}/{total_votes}, 점수: {final_score})")
        else:
            logger.debug(f"[conservative_mix] 최종 신호 없음 (득표수 부족)")

        return StrategyResult(
            strategy_name=f"Voting({votes_buy + votes_sell}/{total_votes})",
            strategy_type=StrategyType.CONSERVATIVE,
            has_signal=has_signal,
            total_score=final_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=evidences,
            signal=None,
            confidence=final_confidence,
            buy_score=final_buy_score,
            sell_score=final_sell_score
        ) 