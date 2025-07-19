"""
전략 조합 매니저 - 전략 믹스 설정 및 조합 로직을 담당
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from domain.signals.models.enums import StrategyType, StrategyMixMode
from infrastructure.db.models.enums import TrendType
from domain.strategies.mixes import StrategyMixConfig, STRATEGY_MIXES
from domain.strategies.base import BaseStrategy
from domain.signals.models.strategy_result import StrategyResult
from domain.orchestration.utils.strategy_manager_utils import StrategyManagerUtils
from infrastructure.logging.logger_config import get_logger

logger = get_logger(__name__)


class StrategyMixManager:
    """전략 조합을 관리하는 매니저"""
    
    def __init__(self):
        self.current_mix_config: Optional[StrategyMixConfig] = None
    
    def set_strategy_mix(self, mix_name: str) -> bool:
        """
        Static Strategy Mix(조합) 설정
        Args:
            mix_name (str): 'balanced_mix', 'aggressive_mix', 'conservative_mix' 등
        Returns:
            bool: 성공 여부
        """
        mix_config = STRATEGY_MIXES.get(mix_name)
        if not mix_config:
            logger.warning(f"알 수 없는 믹스 이름: {mix_name}")
            return False
            
        self.current_mix_config = mix_config
        logger.info(f"전략 조합 설정 완료: {mix_name}")
        return True
    
    def clear_current_mix(self):
        """현재 믹스 설정을 해제합니다."""
        self.current_mix_config = None
        logger.info("현재 전략 조합이 해제되었습니다.")
    
    def analyze_with_strategy_mix(self, 
                                active_strategies: Dict[StrategyType, BaseStrategy],
                                df_with_indicators: pd.DataFrame,
                                ticker: str,
                                market_trend: TrendType,
                                long_term_trend: TrendType,
                                daily_extra_indicators: Dict) -> StrategyResult:
        """전략 조합으로 분석합니다."""
        if not self.current_mix_config:
            raise RuntimeError("설정된 전략 조합이 없습니다.")
        
        # 각 전략 실행하여 개별 결과 수집
        individual_results = self._execute_individual_strategies(
            active_strategies, df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        # 결과 조합
        return self._combine_strategy_results(individual_results)
    
    def _execute_individual_strategies(self,
                                     active_strategies: Dict[StrategyType, BaseStrategy],
                                     df_with_indicators: pd.DataFrame,
                                     ticker: str,
                                     market_trend: TrendType,
                                     long_term_trend: TrendType,
                                     daily_extra_indicators: Dict) -> Dict[StrategyType, Tuple[StrategyResult, float]]:
        """각 전략을 개별적으로 실행하여 결과를 수집합니다."""
        individual_results = {}
        
        for strategy_type, weight in self.current_mix_config.strategies.items():
            if strategy_type in active_strategies:
                strategy = active_strategies[strategy_type]
                result = strategy.analyze(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
                )
                individual_results[strategy_type] = (result, weight)
        
        return individual_results
    
    def _combine_strategy_results(self, 
                                individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """여러 전략 결과를 조합합니다."""
        mode = self.current_mix_config.mode
        
        if mode == StrategyMixMode.WEIGHTED:
            return self._weighted_combination(individual_results)
        elif mode == StrategyMixMode.VOTING:
            return self._voting_combination(individual_results)
        elif mode == StrategyMixMode.ENSEMBLE:
            return self._ensemble_combination(individual_results)
        else:
            # SINGLE 모드는 여기 오면 안됨
            return self._weighted_combination(individual_results)
    
    def _extract_combination_base_data(self, individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> Dict[str, Any]:
        """조합 메서드들의 공통 데이터를 추출합니다."""
        all_signals = []
        strategy_names = []
        
        for strategy_type, (result, weight) in individual_results.items():
            all_signals.extend(result.signals_detected)
            strategy_names.append(f"{result.strategy_name}({weight:.1f})")
        
        return {
            'all_signals': all_signals,
            'strategy_names': strategy_names,
            'total_strategies': len(individual_results)
        }
    
    def _create_combined_result(self,
                              strategy_name: str,
                              has_signal: bool,
                              final_score: float,
                              all_signals: List,
                              confidence: float = 0.0,
                              buy_score: float = 0.0,
                              sell_score: float = 0.0,
                              signal=None) -> StrategyResult:
        """조합된 전략 결과를 생성합니다."""
        return StrategyResult(
            strategy_name=strategy_name,
            strategy_type=StrategyType.BALANCED,  # 조합은 BALANCED로 분류
            has_signal=has_signal,
            total_score=final_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=all_signals,
            signal=signal,
            confidence=confidence,
            buy_score=buy_score,
            sell_score=sell_score
        )
    
    def _weighted_combination(self, 
                            individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """가중치 기반 조합"""
        base_data = self._extract_combination_base_data(individual_results)
        
        # 가중치 계산
        total_weighted_buy_score = 0.0
        total_weighted_sell_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        
        for strategy_type, (result, weight) in individual_results.items():
            total_weighted_buy_score += result.buy_score * weight
            total_weighted_sell_score += result.sell_score * weight
            total_weight += weight
            total_confidence += result.confidence * weight
        
        # 평균 계산
        final_buy_score = total_weighted_buy_score / total_weight if total_weight > 0 else 0
        final_sell_score = total_weighted_sell_score / total_weight if total_weight > 0 else 0
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0
        
        # 임계값 조정 및 신호 결정
        adjusted_threshold = self.current_mix_config.threshold_adjustment * 8.0
        final_score, has_signal = self._determine_signal_from_scores(
            final_buy_score, final_sell_score, adjusted_threshold
        )

        return self._create_combined_result(
            strategy_name=f"Mix({'+'.join(base_data['strategy_names'])})",
            has_signal=has_signal,
            final_score=final_score,
            all_signals=base_data['all_signals'],
            confidence=final_confidence,
            buy_score=final_buy_score,
            sell_score=final_sell_score
        )
    
    def _determine_signal_from_scores(self, buy_score: float, sell_score: float, threshold: float) -> Tuple[float, bool]:
        """매수/매도 점수에서 최종 신호와 점수를 결정합니다."""
        if buy_score > sell_score and buy_score >= threshold:
            return buy_score, True
        elif sell_score > buy_score and sell_score >= threshold:
            return sell_score, True
        return 0, False
    
    def _voting_combination(self, 
                          individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """투표 기반 조합"""
        base_data = self._extract_combination_base_data(individual_results)
        
        buy_votes = 0
        sell_votes = 0
        buy_scores = []
        sell_scores = []
        
        for strategy_type, (result, weight) in individual_results.items():
            if result.has_signal:
                if result.buy_score > result.sell_score:
                    buy_votes += 1
                    buy_scores.append(result.total_score)
                else:
                    sell_votes += 1
                    sell_scores.append(result.total_score)

        majority_threshold = base_data['total_strategies'] / 2
        has_signal = False
        final_score = 0
        signal_type = None

        if buy_votes > majority_threshold and buy_votes > sell_votes:
            has_signal = True
            signal_type = 'BUY'
            final_score = sum(buy_scores) / len(buy_scores) if buy_scores else 0
        elif sell_votes > majority_threshold and sell_votes > buy_votes:
            has_signal = True
            signal_type = 'SELL'
            final_score = sum(sell_scores) / len(sell_scores) if sell_scores else 0

        return self._create_combined_result(
            strategy_name=f"Voting(B:{buy_votes},S:{sell_votes}/{base_data['total_strategies']})",
            has_signal=has_signal,
            final_score=final_score,
            all_signals=base_data['all_signals'],
            confidence=(max(buy_votes, sell_votes) / base_data['total_strategies']) if has_signal else 0,
            buy_score=sum(buy_scores) / len(buy_scores) if buy_scores else 0,
            sell_score=sum(sell_scores) / len(sell_scores) if sell_scores else 0
        )
    
    def _ensemble_combination(self, 
                            individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """앙상블 조합 (고급 기법)"""
        # 간단한 앙상블: 신뢰도가 높은 전략들의 가중 평균
        high_confidence_results = [
            (result, weight) for result, weight in individual_results.values()
            if result.confidence > 0.7
        ]
        
        if not high_confidence_results:
            # 신뢰도 높은 결과가 없으면 일반 가중치 조합
            return self._weighted_combination(individual_results)
        
        # 신뢰도 높은 결과들만으로 재조합
        filtered_results = {
            result.strategy_type: (result, weight) for result, weight in high_confidence_results
        }
        
        return self._weighted_combination(filtered_results)
    
    def get_current_mix_info(self) -> Optional[Dict[str, Any]]:
        """현재 믹스 설정 정보를 반환합니다."""
        if not self.current_mix_config:
            return None
        
        from dataclasses import asdict
        return asdict(self.current_mix_config)
    
    @property
    def has_current_mix(self) -> bool:
        """현재 설정된 믹스가 있는지 확인합니다."""
        return self.current_mix_config is not None