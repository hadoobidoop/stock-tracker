"""
전략 매니저 - 여러 전략을 관리하고 동적으로 교체할 수 있는 시스템

이 모듈은 사용자가 원하는 "갈아끼우며 사용할 수 있는" 전략 시스템을 제공합니다.

# 모든 전략은 domain/strategies/전략명/ 하위에서 독립적으로 관리됩니다.
# 레거시 domain/analysis/strategy/implementations/ 경로는 더 이상 사용하지 않습니다.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd

# Import from new centralized location
from domain.analysis.models.enums import StrategyType, StrategyMixMode
# Static Strategy Mix 관련 설정 import
from domain.strategies.strategy_mixes import (
    StrategyMixConfig, STRATEGY_MIXES
)
# Individual mix configs are now managed centrally via STRATEGY_MIXES
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.dynamic_strategy_manager import DynamicStrategyManager
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.analysis.models.base_strategy import BaseStrategy
from domain.analysis.models.strategy_result import StrategyResult
from .strategy_factory import StrategyFactory

logger = get_logger(__name__)


class StrategyManager:
    """
    전략 매니저 - 정적 전략과 전략 믹스를 관리하고, 동적 전략은 위임합니다.
    """
    
    def __init__(self):
        self.active_strategies: Dict[StrategyType, BaseStrategy] = {}
        self.current_strategy: Optional[BaseStrategy] = None
        self.current_mix_config: Optional[StrategyMixConfig] = None
        
        # 동적 전략 관리는 DynamicStrategyManager에 위임
        self.dynamic_manager = DynamicStrategyManager()
        
        self.performance_history: List[Dict] = []
        self.indicator_cache: Dict[str, Dict] = {}
        self.cache_last_updated: Dict[str, datetime] = {}
        
        # 설정
        self.auto_strategy_selection = False
        self.market_condition_detection = True
    
    # ============================================================================
    # 공통 유틸리티 메서드들 (중복 코드 제거)
    # ============================================================================
    
    def _disable_other_modes(self):
        """다른 모든 모드를 비활성화합니다."""
        self.dynamic_manager.current_strategy = None
        self.current_mix_config = None
    
    def _get_analysis_parameters(self, 
                               df_with_indicators: pd.DataFrame,
                               ticker: str,
                               market_trend: TrendType = TrendType.NEUTRAL,
                               long_term_trend: TrendType = TrendType.NEUTRAL,
                               daily_extra_indicators: Dict = None) -> Dict[str, Any]:
        """분석 파라미터를 표준화된 딕셔너리로 반환합니다."""
        return {
            'df_with_indicators': df_with_indicators,
            'ticker': ticker,
            'market_trend': market_trend,
            'long_term_trend': long_term_trend,
            'daily_extra_indicators': daily_extra_indicators
        }
    
    def _create_strategy_info(self, 
                            strategy_type: StrategyType, 
                            strategy: BaseStrategy, 
                            is_current: bool = False,
                            strategy_class: str = "static") -> Dict[str, Any]:
        """전략 정보를 표준화된 형태로 생성합니다."""
        return {
            "type": strategy_type.value,
            "name": strategy.get_name(),
            "description": strategy.get_description(),
            "is_current": is_current,
            "strategy_class": strategy_class
        }
    
    def _validate_strategy_initialization(self, strategy: Optional[BaseStrategy], strategy_type: StrategyType) -> bool:
        """전략 초기화 결과를 검증합니다."""
        if not strategy or not strategy.initialize():
            logger.error(f"전략 초기화 실패: {strategy_type.value}")
            logger.debug(f"[진단] 등록 실패: {strategy_type}, 현재 등록된 전략: {[k.value for k in self.active_strategies.keys()]}")
            return False
        return True
    
    # ============================================================================
    # 전략 초기화 및 관리
    # ============================================================================
        
    def initialize_strategies(self, strategy_types: Optional[List[StrategyType]] = None) -> bool:
        """전략들을 초기화합니다."""
        if strategy_types is None:
            # 기본적으로 모든 정적 전략을 로드
            strategy_types = StrategyFactory.get_available_static_strategies()
        
        logger.info(f"전략 초기화 시작: {len(strategy_types)}개 정적 전략")
        
        # 정적 전략 초기화
        static_success_count = self._initialize_static_strategies(strategy_types)
        
        # 동적 전략 초기화 (위임)
        dynamic_success_count = self.dynamic_manager.initialize()
        
        # 기본 전략 설정
        self._set_default_strategy()
        
        total_success = static_success_count + dynamic_success_count
        logger.info(f"전략 초기화 완료: {static_success_count}/{len(strategy_types)} 정적 전략, {dynamic_success_count} 동적 전략")
        
        return total_success > 0
    
    def _initialize_static_strategies(self, strategy_types: List[StrategyType]) -> int:
        """정적 전략들을 초기화"""
        success_count = 0
        for strategy_type in strategy_types:
            try:
                strategy = StrategyFactory.create_static_strategy(strategy_type)
                if self._validate_strategy_initialization(strategy, strategy_type):
                    self.active_strategies[strategy_type] = strategy
                    success_count += 1
                    logger.info(f"정적 전략 초기화 성공: {strategy.get_name()}")
                    logger.debug(f"[진단] 등록 성공: {strategy_type}, 현재 등록된 전략: {[k.value for k in self.active_strategies.keys()]}")
            except Exception as e:
                logger.error(f"정적 전략 초기화 실패 {strategy_type}: {e}")
                logger.debug(f"[진단] 예외 발생: {strategy_type}, 현재 등록된 전략: {[k.value for k in self.active_strategies.keys()]}")
                continue
        return success_count
    
    def _set_default_strategy(self):
        """기본 전략을 설정하고 다른 모드는 비활성화합니다."""
        # 1. 기본 정적 전략 설정
        if StrategyType.BALANCED in self.active_strategies:
            self.current_strategy = self.active_strategies[StrategyType.BALANCED]
        elif self.active_strategies:
            self.current_strategy = list(self.active_strategies.values())[0]
        
        # 2. 다른 모든 모드 비활성화
        self._disable_other_modes()
        
        if self.current_strategy:
            logger.info(f"기본 전략 설정: {self.current_strategy.get_name()} (다른 모든 모드 비활성화)")
    
    def add_strategy(self, strategy_type: StrategyType, strategy: Optional[BaseStrategy] = None) -> bool:
        """전략 추가"""
        if strategy is None:
            strategy = StrategyFactory.create_static_strategy(strategy_type)

        if not self._validate_strategy_initialization(strategy, strategy_type):
            return False
        
        self.active_strategies[strategy_type] = strategy
        logger.info(f"전략 추가 성공: {strategy.get_name()}")
        return True
    
    def set_strategy(self, strategy: Optional[BaseStrategy]):
        """
        외부에서 생성된 전략 객체를 직접 설정합니다. (주로 동적 전략 백테스팅용)
        """
        if strategy is None:
            # None으로 설정하면 기본 정적 전략으로 리셋
            self._set_default_strategy()
            logger.info("전략이 None으로 설정되어 기본 전략으로 리셋합니다.")
            return

        # 전략의 종류에 따라 적절한 매니저에 할당
        from domain.strategies.dynamic_strategies.dynamic_strategy_manager.dynamic_strategy import DynamicCompositeStrategy
        if isinstance(strategy, DynamicCompositeStrategy):
            self.dynamic_manager.current_strategy = strategy
            self.current_strategy = None
            self.current_mix_config = None
            logger.info(f"동적 전략 직접 설정: {strategy.strategy_name}")
        elif isinstance(strategy, BaseStrategy):
            # 정적 전략인 경우
            self.current_strategy = strategy
            self._disable_other_modes()
            logger.info(f"정적 전략 직접 설정: {strategy.get_name()}")
        else:
            logger.error(f"알 수 없는 타입의 전략 객체입니다: {type(strategy)}")

    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """정적 전략 교체"""
        if strategy_type not in self.active_strategies:
            logger.warning(f"전략이 로드되지 않음: {strategy_type}")
            return False
        
        self.current_strategy = self.active_strategies[strategy_type]
        self._disable_other_modes()
        
        logger.info(f"전략 교체 완료: {self.current_strategy.get_name()}")
        return True
    
    def set_strategy_mix(self, mix_name: str) -> bool:
        """
        Static Strategy Mix(조합) 설정
        Args:
            mix_name (str): 'balanced_mix', 'aggressive_mix', 'conservative_mix' 등
        Returns:
            bool: 성공 여부
        """
        mix_config = self._get_mix_config(mix_name)
        if not mix_config:
            logger.warning(f"알 수 없는 믹스 이름: {mix_name}")
            return False
            
        self.current_mix_config = mix_config
        self.current_strategy = None  # 단일 전략 비활성화
        self.dynamic_manager.current_strategy = None  # 동적 전략 비활성화

        logger.info(f"전략 조합 설정 완료: {mix_name}")
        return True

    def _get_mix_config(self, mix_name: str) -> Optional[StrategyMixConfig]:
        """믹스 설정을 가져옵니다."""
        return STRATEGY_MIXES.get(mix_name)

    def switch_to_dynamic_strategy(self, strategy_name: str) -> bool:
        """동적 전략으로 교체 (DynamicStrategyManager에 위임)"""
        if self.dynamic_manager.switch_strategy(strategy_name):
            self.current_strategy = None
            self.current_mix_config = None
            return True
        return False
    
    @property
    def active_strategy(self) -> Optional[BaseStrategy]:
        """현재 활성화된 단일 전략 객체를 반환합니다 (동적 또는 정적)."""
        if self.dynamic_manager.current_strategy:
            return self.dynamic_manager.current_strategy
        if self.current_strategy:
            return self.current_strategy
        return None

    # ============================================================================
    # 전략 분석 및 실행
    # ============================================================================

    def analyze_with_current_strategy(self, 
                                    df_with_indicators: pd.DataFrame,
                                    ticker: str,
                                    market_trend: TrendType = TrendType.NEUTRAL,
                                    long_term_trend: TrendType = TrendType.NEUTRAL,
                                    daily_extra_indicators: Dict = None) -> StrategyResult:
        """현재 활성화된 전략으로 분석합니다."""
        
        # 자동 전략 선택이 활성화된 경우
        if self.auto_strategy_selection:
            self._auto_select_strategy(market_trend, df_with_indicators)
        
        # 분석 파라미터 표준화
        analysis_params = self._get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        # 실제 분석을 수행할 전략 객체 가져오기
        strategy_to_run = self.active_strategy

        if strategy_to_run:
             return strategy_to_run.analyze(**analysis_params)
        elif self.current_mix_config:
            return self._analyze_with_strategy_mix(**analysis_params)
        else:
            raise RuntimeError("활성화된 전략이 없습니다.")
    
    def analyze_with_all_strategies(self,
                                  df_with_indicators: pd.DataFrame,
                                  ticker: str,
                                  market_trend: TrendType = TrendType.NEUTRAL,
                                  long_term_trend: TrendType = TrendType.NEUTRAL,
                                  daily_extra_indicators: Dict = None) -> Dict[StrategyType, StrategyResult]:
        """모든 활성화된 정적 전략으로 분석합니다."""
        analysis_params = self._get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        results = {}
        for strategy_type, strategy in self.active_strategies.items():
            result = strategy.analyze(**analysis_params)
            results[strategy_type] = result
        return results

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """사용 가능한 전략 목록을 반환합니다."""
        strategies = []
        
        # 정적 전략
        for strategy_type, strategy in self.active_strategies.items():
            strategy_info = self._create_strategy_info(
                strategy_type, 
                strategy, 
                is_current=(strategy == self.current_strategy),
                strategy_class="static"
            )
            strategies.append(strategy_info)
        
        # 동적 전략 (위임)
        for name in self.dynamic_manager.list_strategies():
            info = self.dynamic_manager.get_strategy_info(name)
            if info:
                strategies.append({
                    "type": "DYNAMIC",
                    "name": name,
                    "description": info.get("description", "Dynamic strategy"),
                    "is_current": info.get("is_current", False),
                    "strategy_class": "dynamic"
                })
            
        return strategies
    
    # ============================================================================
    # 전략 조합 (Strategy Mix) 관련 메서드들
    # ============================================================================
    
    def _analyze_with_strategy_mix(self, 
                                 df_with_indicators: pd.DataFrame,
                                 ticker: str,
                                 market_trend: TrendType,
                                 long_term_trend: TrendType,
                                 daily_extra_indicators: Dict) -> StrategyResult:
        """전략 조합으로 분석합니다."""
        
        # 각 전략 실행하여 개별 결과 수집
        individual_results = self._execute_individual_strategies(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        # 결과 조합
        return self._combine_strategy_results(individual_results)
    
    def _execute_individual_strategies(self,
                                     df_with_indicators: pd.DataFrame,
                                     ticker: str,
                                     market_trend: TrendType,
                                     long_term_trend: TrendType,
                                     daily_extra_indicators: Dict) -> Dict[StrategyType, Tuple[StrategyResult, float]]:
        """각 전략을 개별적으로 실행하여 결과를 수집합니다."""
        individual_results = {}
        
        for strategy_type, weight in self.current_mix_config.strategies.items():
            if strategy_type in self.active_strategies:
                strategy = self.active_strategies[strategy_type]
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

        best_result = max(individual_results.values(), key=lambda x: x[0].total_score)[0]

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
    
    # ============================================================================
    # 자동 전략 선택 및 성능 관리
    # ============================================================================
    
    def _auto_select_strategy(self, market_trend: TrendType, df: pd.DataFrame):
        """시장 상황에 따라 자동으로 전략을 선택합니다."""
        if not self.market_condition_detection:
            return

        # 1. 시장 상황 분석 및 전략 추천 받기
        recommended_strategy = self._get_recommended_strategy_for_market(market_trend)
        if not recommended_strategy:
            return

        # 2. 추천받은 전략으로 교체
        self._apply_recommended_strategy(recommended_strategy, market_trend)
    
    def _get_recommended_strategy_for_market(self, market_trend: TrendType) -> Optional[Tuple[Any, str]]:
        """시장 상황에 대한 추천 전략을 가져옵니다."""
        market_condition = market_trend.value  # 예: 'BULLISH'
        
        # StrategySelector의 전역 인스턴스 사용
        from domain.analysis.utils.strategy_selector import strategy_selector
        
        recommended_strategy = strategy_selector.get_recommended_strategy(market_condition)
        if not recommended_strategy:
            logger.warning(f"시장 상황 '{market_condition}'에 대한 추천 전략을 찾지 못했습니다.")
            return None
        
        return recommended_strategy
    
    def _apply_recommended_strategy(self, recommended_strategy: Tuple[Any, str], market_trend: TrendType):
        """추천받은 전략을 적용합니다."""
        strategy_id, strategy_class = recommended_strategy
        market_condition = market_trend.value

        try:
            if strategy_class == 'static':
                self._switch_to_static_if_different(strategy_id, market_condition)
            elif strategy_class == 'dynamic':
                self._switch_to_dynamic_if_different(strategy_id, market_condition)
        except Exception as e:
            logger.error(f"추천 전략({strategy_id})으로 교체 중 오류 발생: {e}")
    
    def _switch_to_static_if_different(self, strategy_id: StrategyType, market_condition: str):
        """현재 전략과 다른 경우에만 정적 전략으로 교체합니다."""
        if self.current_strategy is None or self.current_strategy.strategy_type != strategy_id:
            self.switch_strategy(strategy_id)
            logger.info(f"시장 상황 '{market_condition}'에 따라 정적 전략 자동 선택: {strategy_id.value}")
    
    def _switch_to_dynamic_if_different(self, strategy_id: str, market_condition: str):
        """현재 전략과 다른 경우에만 동적 전략으로 교체합니다."""
        if (self.dynamic_manager.current_strategy is None or 
            self.dynamic_manager.current_strategy.strategy_name != strategy_id):
            self.switch_to_dynamic_strategy(strategy_id)
            logger.info(f"시장 상황 '{market_condition}'에 따라 동적 전략 자동 선택: {strategy_id}")
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """전략별 성능 요약을 반환합니다."""
        performance = {}
        
        for strategy_type, strategy in self.active_strategies.items():
            performance[strategy_type.value] = strategy.get_performance_metrics()
        
        return performance
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """현재 전략 정보를 반환합니다."""
        if self.dynamic_manager.current_strategy:
            return {
                "mode": "dynamic", 
                "strategy": self.dynamic_manager.get_strategy_info()
            }
        elif self.current_mix_config:
            return {
                "mode": "mix", 
                "mix_config": asdict(self.current_mix_config)
            }
        elif self.current_strategy:
            return {
                "mode": "single", 
                "strategy": {
                    "name": self.current_strategy.get_name(), 
                    "type": self.current_strategy.strategy_type.value
                }
            }
        return {"mode": "none"}
    
    def enable_auto_strategy_selection(self, enable: bool = True):
        """자동 전략 선택 활성화/비활성화"""
        self.auto_strategy_selection = enable
        logger.info(f"자동 전략 선택: {'활성화' if enable else '비활성화'}") 