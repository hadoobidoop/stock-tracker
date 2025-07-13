"""
전략 매니저 - 여러 전략을 관리하고 동적으로 교체할 수 있는 시스템

이 모듈은 사용자가 원하는 "갈아끼우며 사용할 수 있는" 전략 시스템을 제공합니다.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
from dataclasses import asdict

from infrastructure.db.models.enums import TrendType
from domain.analysis.config.static_strategies import (
    StrategyType, StrategyConfig, STRATEGY_CONFIGS, get_static_strategy_types
)
# Static Strategy Mix 관련 설정 import
from domain.analysis.config.strategy_mixes import (
    StrategyMixMode, StrategyMixConfig, STRATEGY_MIXES
)

from .base_strategy import BaseStrategy, StrategyResult
from .strategy_factory import StrategyFactory
from .dynamic_strategy_manager import DynamicStrategyManager
from infrastructure.logging import get_logger

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
        
    def initialize_strategies(self, strategy_types: Optional[List[StrategyType]] = None) -> bool:
        """전략들을 초기화합니다."""
        if strategy_types is None:
            # 기본적으로 모든 정적 전략을 로드
            strategy_types = get_static_strategy_types()
        
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
                if strategy and strategy.initialize():
                    self.active_strategies[strategy_type] = strategy
                    success_count += 1
                    logger.info(f"정적 전략 초기화 성공: {strategy.get_name()}")
                    logger.debug(f"[진단] 등록 성공: {strategy_type}, 현재 등록된 전략: {[k.value for k in self.active_strategies.keys()]}")
                else:
                    logger.error(f"정적 전략 초기화 실패: {strategy_type.value}")
                    logger.debug(f"[진단] 등록 실패: {strategy_type}, 현재 등록된 전략: {[k.value for k in self.active_strategies.keys()]}")
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
        self.dynamic_manager.current_strategy = None
        self.current_mix_config = None
        
        if self.current_strategy:
            logger.info(f"기본 전략 설정: {self.current_strategy.get_name()} (다른 모든 모드 비활성화)")
    
    def add_strategy(self, strategy_type: StrategyType, strategy: Optional[BaseStrategy] = None) -> bool:
        """전략 추가"""
        if strategy is None:
            strategy = StrategyFactory.create_static_strategy(strategy_type)

        if not strategy or not strategy.initialize():
            logger.error(f"전략 초기화 실패: {strategy_type}")
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
            self.dynamic_manager.current_strategy = None
            self.current_mix_config = None
            logger.info("전략이 None으로 설정되어 기본 전략으로 리셋합니다.")
            return

        # 전략의 종류에 따라 적절한 매니저에 할당
        from .dynamic_strategy import DynamicCompositeStrategy
        if isinstance(strategy, DynamicCompositeStrategy):
            self.dynamic_manager.current_strategy = strategy
            self.current_strategy = None
            self.current_mix_config = None
            logger.info(f"동적 전략 직접 설정: {strategy.strategy_name}")
        elif isinstance(strategy, BaseStrategy):
            # 정적 전략인 경우
            self.current_strategy = strategy
            self.dynamic_manager.current_strategy = None
            self.current_mix_config = None
            logger.info(f"정적 전략 직접 설정: {strategy.get_name()}")
        else:
            logger.error(f"알 수 없는 타입의 전략 객체입니다: {type(strategy)}")

    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """정적 전략 교체"""
        if strategy_type not in self.active_strategies:
            logger.warning(f"전략이 로드되지 않음: {strategy_type}")
            return False
        
        self.current_strategy = self.active_strategies[strategy_type]
        self.dynamic_manager.current_strategy = None  # 동적 전략 비활성화
        self.current_mix_config = None  # 조합 모드 비활성화
        
        logger.info(f"전략 교체 완료: {self.current_strategy.get_name()}")
        return True
    
    def set_strategy_mix(self, mix_name: str) -> bool:
        """전략 조합을 설정합니다."""
        mix_config = STRATEGY_MIXES.get(mix_name)
        if not mix_config:
            logger.warning(f"전략 조합 설정을 찾을 수 없음: {mix_name}")
            return False

        self.current_mix_config = mix_config
        self.current_strategy = None  # 단일 전략 비활성화
        self.dynamic_manager.current_strategy = None  # 동적 전략 비활성화

        logger.info(f"전략 조합 설정 완료: {mix_name}")
        return True

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
        
        # 실제 분석을 수행할 전략 객체 가져오기
        strategy_to_run = self.active_strategy

        if strategy_to_run:
             return strategy_to_run.analyze(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
        elif self.current_mix_config:
            return self._analyze_with_strategy_mix(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
        else:
            raise RuntimeError("활성화된 전략이 없습니다.")
    
    def analyze_with_all_strategies(self,
                                  df_with_indicators: pd.DataFrame,
                                  ticker: str,
                                  market_trend: TrendType = TrendType.NEUTRAL,
                                  long_term_trend: TrendType = TrendType.NEUTRAL,
                                  daily_extra_indicators: Dict = None) -> Dict[StrategyType, StrategyResult]:
        """모든 활성화된 정적 전략으로 분석합니다."""
        results = {}
        for strategy_type, strategy in self.active_strategies.items():
            result = strategy.analyze(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
            results[strategy_type] = result
        return results

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """사용 가능한 전략 목록을 반환합니다."""
        strategies = []
        
        # 정적 전략
        for strategy_type, strategy in self.active_strategies.items():
            strategies.append({
                "type": strategy_type.value,
                "name": strategy.get_name(),
                "description": strategy.config.description,
                "is_current": strategy == self.current_strategy,
                "strategy_class": "static"
            })
        
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
    
    def _analyze_with_strategy_mix(self, 
                                 df_with_indicators: pd.DataFrame,
                                 ticker: str,
                                 market_trend: TrendType,
                                 long_term_trend: TrendType,
                                 daily_extra_indicators: Dict) -> StrategyResult:
        """전략 조합으로 분석합니다."""
        
        individual_results = {}
        
        # 각 전략 실행
        for strategy_type, weight in self.current_mix_config.strategies.items():
            if strategy_type in self.active_strategies:
                strategy = self.active_strategies[strategy_type]
                result = strategy.analyze(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
                )
                individual_results[strategy_type] = (result, weight)
        
        # 결과 조합
        return self._combine_strategy_results(individual_results)
    
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
    
    def _weighted_combination(self, 
                            individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """가중치 기반 조합"""
        total_weighted_buy_score = 0.0
        total_weighted_sell_score = 0.0
        total_weight = 0.0
        all_signals = []
        total_confidence = 0.0
        
        strategy_names = []
        
        for strategy_type, (result, weight) in individual_results.items():
            total_weighted_buy_score += result.buy_score * weight
            total_weighted_sell_score += result.sell_score * weight
            total_weight += weight
            total_confidence += result.confidence * weight
            
            all_signals.extend(result.signals_detected)
            strategy_names.append(f"{result.strategy_name}({weight:.1f})")
        
        # 평균 계산
        final_buy_score = total_weighted_buy_score / total_weight if total_weight > 0 else 0
        final_sell_score = total_weighted_sell_score / total_weight if total_weight > 0 else 0
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0
        
        # 임계값 조정
        adjusted_threshold = self.current_mix_config.threshold_adjustment * 8.0  # 기본 임계값
        
        final_score = 0
        has_signal = False
        if final_buy_score > final_sell_score and final_buy_score >= adjusted_threshold:
            final_score = final_buy_score
            has_signal = True
        elif final_sell_score > final_buy_score and final_sell_score >= adjusted_threshold:
            final_score = final_sell_score
            has_signal = True

        return StrategyResult(
            strategy_name=f"Mix({'+'.join(strategy_names)})",
            strategy_type=StrategyType.BALANCED,  # 조합은 BALANCED로 분류
            has_signal=has_signal,
            total_score=final_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=all_signals,
            signal=None,  # 필요시 별도 생성
            confidence=final_confidence,
            buy_score=final_buy_score,
            sell_score=final_sell_score
        )
    
    def _voting_combination(self, 
                          individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """투표 기반 조합"""
        buy_votes = 0
        sell_votes = 0
        buy_scores = []
        sell_scores = []
        all_signals = []
        
        total_strategies = len(individual_results)
        
        for strategy_type, (result, weight) in individual_results.items():
            if result.has_signal:
                if result.buy_score > result.sell_score:
                    buy_votes += 1
                    buy_scores.append(result.total_score)
                else:
                    sell_votes += 1
                    sell_scores.append(result.total_score)
            all_signals.extend(result.signals_detected)

        majority_threshold = total_strategies / 2
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

        return StrategyResult(
            strategy_name=f"Voting(B:{buy_votes},S:{sell_votes}/{total_strategies})",
            strategy_type=StrategyType.BALANCED,
            has_signal=has_signal,
            total_score=final_score,
            signal_strength="",
            signals_detected=all_signals,
            signal=best_result.signal if has_signal else None,
            confidence=(max(buy_votes, sell_votes) / total_strategies) if has_signal else 0,
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
    
    def _auto_select_strategy(self, market_trend: TrendType, df: pd.DataFrame):
        """시장 상황에 따라 자동으로 전략을 선택합니다."""
        if not self.market_condition_detection:
            return

        # 1. StrategySelector를 통해 시장 상황 분석 및 전략 추천 받기
        # (이 프로젝트에서는 market_trend를 그대로 market_condition으로 사용)
        market_condition = market_trend.value  # 예: 'BULLISH'
        
        # StrategySelector의 전역 인스턴스 사용
        from domain.analysis.utils.strategy_selector import strategy_selector
        
        recommended_strategy = strategy_selector.get_recommended_strategy(market_condition)

        if not recommended_strategy:
            logger.warning(f"시장 상황 '{market_condition}'에 대한 추천 전략을 찾지 못했습니다.")
            return

        strategy_id, strategy_class = recommended_strategy

        # 2. 추천받은 전략으로 교체
        try:
            if strategy_class == 'static':
                # 현재 전략과 다른 경우에만 교체
                if self.current_strategy is None or self.current_strategy.strategy_type != strategy_id:
                    self.switch_strategy(strategy_id)
                    logger.info(f"시장 상황 '{market_condition}'에 따라 정적 전략 자동 선택: {strategy_id.value}")
            
            elif strategy_class == 'dynamic':
                # 현재 전략과 다른 경우에만 교체
                if self.dynamic_manager.current_strategy is None or self.dynamic_manager.current_strategy.strategy_name != strategy_id:
                    self.switch_to_dynamic_strategy(strategy_id)
                    logger.info(f"시장 상황 '{market_condition}'에 따라 동적 전략 자동 선택: {strategy_id}")
        except Exception as e:
            logger.error(f"추천 전략({strategy_id})으로 교체 중 오류 발생: {e}")
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """전략별 성능 요약을 반환합니다."""
        performance = {}
        
        for strategy_type, strategy in self.active_strategies.items():
            performance[strategy_type.value] = strategy.get_performance_metrics()
        
        return performance
    
    def save_strategies_to_file(self, file_path: str):
        """전략 설정을 파일로 저장합니다."""
        configs = {}
        for strategy_type, strategy in self.active_strategies.items():
            configs[strategy_type.value] = asdict(strategy.config)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False, default=str)
    
    def load_strategies_from_file(self, file_path: str) -> bool:
        """파일에서 전략 설정을 로드합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            # 기존 전략 정리
            self.active_strategies.clear()
            
            # 새 전략 로드
            for strategy_type_str, config_dict in configs.items():
                strategy_type = StrategyType(strategy_type_str)
                # config_dict를 StrategyConfig 객체로 변환하는 로직 필요
                # 여기서는 간단히 기본 설정 사용
                config = STRATEGY_CONFIGS.get(strategy_type)
                if config:
                    strategy = StrategyFactory.create_strategy(strategy_type, config)
                    self.active_strategies[strategy_type] = strategy
            
            logger.info(f"전략 설정 로드 완료: {len(self.active_strategies)}개 전략")
            return True
            
        except Exception as e:
            logger.error(f"전략 설정 로드 실패: {e}")
            return False
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """현재 전략 정보를 반환합니다."""
        if self.dynamic_manager.current_strategy:
            return {"mode": "dynamic", "strategy": self.dynamic_manager.get_strategy_info()}
        elif self.current_mix_config:
            return {"mode": "mix", "mix_config": asdict(self.current_mix_config)}
        elif self.current_strategy:
            return {"mode": "single", "strategy": {"name": self.current_strategy.get_name(), "type": self.current_strategy.strategy_type.value}}
        return {"mode": "none"}
    
    def enable_auto_strategy_selection(self, enable: bool = True):
        """자동 전략 선택 활성화/비활성화"""
        self.auto_strategy_selection = enable
        logger.info(f"자동 전략 선택: {'활성화' if enable else '비활성화'}") 