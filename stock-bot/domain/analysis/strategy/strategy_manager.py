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
# Static Strategy Mix 관련은 legacy_config_backup에서 임시로 참조
try:
    from legacy_config_backup.strategy_settings import (
        StrategyMixMode, StrategyMixConfig, STRATEGY_MIXES,
        MARKET_CONDITION_STRATEGIES
    )
except ImportError:
    # 조합 기능 비활성화를 위한 더미 클래스들
    from enum import Enum
    from dataclasses import dataclass
    from typing import Dict
    
    class StrategyMixMode(Enum):
        WEIGHTED = "weighted"
        VOTING = "voting"
        ENSEMBLE = "ensemble"
    
    @dataclass
    class StrategyMixConfig:
        mode: StrategyMixMode
        strategies: Dict
        threshold_adjustment: float = 1.0
    
    STRATEGY_MIXES = {}
    MARKET_CONDITION_STRATEGIES = {}

from .base_strategy import BaseStrategy, StrategyResult
from .strategy_implementations import StrategyFactory
from .dynamic_strategy import DynamicCompositeStrategy
from domain.analysis.config.dynamic_strategies import get_all_strategies
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StrategyManager:
    """
    전략 매니저 - 여러 전략을 동적으로 관리
    
    특징:
    1. 여러 전략을 동시에 로드하고 관리
    2. 런타임에 전략 교체 가능
    3. 전략 조합 및 앙상블 지원
    4. 시장 상황에 따른 자동 전략 선택
    5. 성능 모니터링 및 백테스트 지원
    """
    
    def __init__(self):
        self.active_strategies: Dict[StrategyType, BaseStrategy] = {}
        self.dynamic_strategies: Dict[str, DynamicCompositeStrategy] = {}
        self.current_strategy: Optional[BaseStrategy] = None
        self.current_dynamic_strategy: Optional[DynamicCompositeStrategy] = None
        self.current_mix_config: Optional[StrategyMixConfig] = None
        self.performance_history: List[Dict] = []
        
        # 지표 캐시 (모든 전략이 공유)
        self.indicator_cache: Dict[str, Dict] = {}
        self.cache_last_updated: Dict[str, datetime] = {}
        
        # 설정
        self.auto_strategy_selection = False
        self.market_condition_detection = True
        self.enable_dynamic_strategies = True
        
    def initialize_strategies(self, strategy_types: Optional[List[StrategyType]] = None) -> bool:
        """전략들을 초기화합니다."""
        if strategy_types is None:
            # 기본적으로 모든 정적 전략을 로드
            strategy_types = get_static_strategy_types()
        
        logger.info(f"전략 초기화 시작: {len(strategy_types)}개 정적 전략")
        
        # 정적 전략 초기화
        static_success_count = self._initialize_static_strategies(strategy_types)
        
        # 동적 전략 초기화
        dynamic_success_count = 0
        if self.enable_dynamic_strategies:
            dynamic_success_count = self._initialize_dynamic_strategies()
        
        # 기본 전략 설정
        self._set_default_strategies()
        
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
                else:
                    logger.error(f"정적 전략 초기화 실패: {strategy_type.value}")
                
            except Exception as e:
                logger.error(f"정적 전략 초기화 실패 {strategy_type}: {e}")
                continue
        
        return success_count
    
    def _initialize_dynamic_strategies(self) -> int:
        """동적 전략들을 초기화"""
        try:
            dynamic_strategy_definitions = get_all_strategies()
            success_count = 0
            
            for strategy_name in dynamic_strategy_definitions.keys():
                try:
                    strategy = StrategyFactory.create_dynamic_strategy(strategy_name)
                    
                    if strategy and strategy.initialize():
                        self.dynamic_strategies[strategy_name] = strategy
                        success_count += 1
                        logger.info(f"동적 전략 초기화 성공: {strategy_name}")
                    else:
                        logger.error(f"동적 전략 초기화 실패: {strategy_name}")
                        
                except Exception as e:
                    logger.error(f"동적 전략 초기화 실패 {strategy_name}: {e}")
                    continue
            
            return success_count
            
        except Exception as e:
            logger.error(f"동적 전략 초기화 전체 실패: {e}")
            return 0
    
    def _set_default_strategies(self):
        """기본 전략 설정"""
        # 기본 정적 전략 설정
        if StrategyType.BALANCED in self.active_strategies:
            self.current_strategy = self.active_strategies[StrategyType.BALANCED]
        elif self.active_strategies:
            self.current_strategy = list(self.active_strategies.values())[0]
        
        # 기본 동적 전략 설정
        if "dynamic_weight_strategy" in self.dynamic_strategies:
            self.current_dynamic_strategy = self.dynamic_strategies["dynamic_weight_strategy"]
        elif self.dynamic_strategies:
            # self.dynamic_strategies.values()는 DynamicCompositeStrategy 객체의 뷰를 반환합니다.
            # 이 뷰에서 첫 번째 항목을 가져와도 타입은 일치합니다.
            self.current_dynamic_strategy = next(iter(self.dynamic_strategies.values()))
        
        if self.current_strategy:
            logger.info(f"기본 정적 전략 설정: {self.current_strategy.get_name()}")
        if self.current_dynamic_strategy:
            logger.info(f"기본 동적 전략 설정: {self.current_dynamic_strategy.strategy_name}")
    
    def add_strategy(self, strategy_type: Union[StrategyType, str], strategy: Optional[BaseStrategy] = None) -> bool:
        """전략 추가"""
        if strategy is None:
            # 전략 타입에 따라 자동 생성
            if isinstance(strategy_type, StrategyType):
                strategy = StrategyFactory.create_static_strategy(strategy_type)
            elif isinstance(strategy_type, str):
                strategy = StrategyFactory.create_dynamic_strategy(strategy_type)
            else:
                logger.error(f"지원되지 않는 전략 타입: {strategy_type}")
                return False
        
        if not strategy or not strategy.initialize():
            logger.error(f"전략 초기화 실패: {strategy_type}")
            return False
        
        # 전략 저장
        if isinstance(strategy, DynamicCompositeStrategy):
            if isinstance(strategy_type, str):
                self.dynamic_strategies[strategy_type] = strategy
            else:
                # 이 경우는 발생해서는 안 되지만, 안전을 위해 로깅
                logger.error(f"Dynamic strategy must have a string name, got {strategy_type}")
                return False
        elif isinstance(strategy, BaseStrategy):
            if isinstance(strategy_type, StrategyType):
                self.active_strategies[strategy_type] = strategy
            else:
                logger.error(f"Static strategy must have a StrategyType enum, got {strategy_type}")
                return False
        
        logger.info(f"전략 추가 성공: {strategy.get_name() if hasattr(strategy, 'get_name') else strategy_type}")
        return True
    
    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """정적 전략 교체"""
        if strategy_type not in self.active_strategies:
            logger.warning(f"전략이 로드되지 않음: {strategy_type}")
            return False
        
        self.current_strategy = self.active_strategies[strategy_type]
        self.current_dynamic_strategy = None  # 동적 전략 비활성화
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
        self.current_dynamic_strategy = None  # 동적 전략 비활성화

        logger.info(f"전략 조합 설정 완료: {mix_name}")
        return True

    def switch_to_dynamic_strategy(self, strategy_name: str) -> bool:
        """동적 전략으로 교체"""
        if strategy_name not in self.dynamic_strategies:
            logger.warning(f"동적 전략이 로드되지 않음: {strategy_name}")
            return False
        
        self.current_dynamic_strategy = self.dynamic_strategies[strategy_name]
        self.current_strategy = None  # 정적 전략 비활성화
        self.current_mix_config = None  # 조합 모드 비활성화
        
        logger.info(f"동��� 전략 교체 완료: {strategy_name}")
        return True
    
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
        
        # 전략 실행 우선순위: 동적 -> 조합 -> 정적
        if self.current_dynamic_strategy:
            return self.current_dynamic_strategy.analyze(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
        elif self.current_mix_config:
            return self._analyze_with_strategy_mix(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
        elif self.current_strategy:
            return self.current_strategy.analyze(
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
                "threshold": strategy.config.signal_threshold,
                "risk_per_trade": strategy.config.risk_per_trade,
                "is_current": strategy == self.current_strategy,
                "strategy_class": "static"
            })
        
        # 동적 전략
        for strategy_name, strategy in self.dynamic_strategies.items():
            strategies.append({
                "type": "DYNAMIC",
                "name": strategy_name,
                "description": strategy.strategy_config.get("description", "Dynamic strategy"),
                "threshold": strategy.strategy_config.get("signal_threshold", 0),
                "risk_per_trade": strategy.strategy_config.get("risk_per_trade", 0),
                "is_current": strategy == self.current_dynamic_strategy,
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
        total_weighted_score = 0.0
        total_weight = 0.0
        all_signals = []
        total_confidence = 0.0
        
        strategy_names = []
        
        for strategy_type, (result, weight) in individual_results.items():
            weighted_score = result.total_score * weight
            total_weighted_score += weighted_score
            total_weight += weight
            total_confidence += result.confidence * weight
            
            all_signals.extend(result.signals_detected)
            strategy_names.append(f"{result.strategy_name}({weight:.1f})")
        
        # 평균 계산
        final_score = total_weighted_score / total_weight if total_weight > 0 else 0
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0
        
        # 임계값 조정
        adjusted_threshold = self.current_mix_config.threshold_adjustment * 8.0  # 기본 임계값
        
        return StrategyResult(
            strategy_name=f"Mix({'+'.join(strategy_names)})",
            strategy_type=StrategyType.BALANCED,  # 조합은 BALANCED로 분류
            has_signal=final_score >= adjusted_threshold,
            total_score=final_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=all_signals,
            signal=None,  # 필요시 별도 생성
            confidence=final_confidence
        )
    
    def _voting_combination(self, 
                          individual_results: Dict[StrategyType, Tuple[StrategyResult, float]]) -> StrategyResult:
        """투표 기반 조합"""
        vote_count = 0
        total_strategies = len(individual_results)
        
        for strategy_type, (result, weight) in individual_results.items():
            if result.has_signal:
                vote_count += 1
        
        # 과반수 이상이 신호를 생성한 경우
        majority_threshold = total_strategies / 2
        has_majority_signal = vote_count > majority_threshold
        
        # 최고 점수 전략 선택
        best_result = max(individual_results.values(), key=lambda x: x[0].total_score)[0]
        
        return StrategyResult(
            strategy_name=f"Voting({vote_count}/{total_strategies})",
            strategy_type=StrategyType.BALANCED,
            has_signal=has_majority_signal,
            total_score=best_result.total_score,
            signal_strength="",  # __post_init__에서 자동 계산
            signals_detected=best_result.signals_detected,
            signal=best_result.signal if has_majority_signal else None,
            confidence=vote_count / total_strategies
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
        
        # 시장 상황 분석
        market_condition = self._analyze_market_condition(market_trend, df)
        
        # 해당 상황에 맞는 전략 선택
        condition_strategies = MARKET_CONDITION_STRATEGIES.get(market_condition, {})
        
        for priority in ["primary", "secondary", "fallback"]:
            strategy_type = condition_strategies.get(priority)
            if strategy_type and strategy_type in self.active_strategies:
                if self.current_strategy is None or self.current_strategy.strategy_type != strategy_type:
                    self.switch_strategy(strategy_type)
                    logger.info(f"시장 상황 '{market_condition}'에 따라 전략 자동 선택: {strategy_type}")
                break
    
    def _analyze_market_condition(self, market_trend: TrendType, df: pd.DataFrame) -> str:
        """시장 상황을 분석합니다."""
        if df.empty:
            return "NEUTRAL"
        
        # 변동성 분석
        if 'atr' in df.columns:
            recent_atr = df['atr'].iloc[-5:].mean()
            long_term_atr = df['atr'].mean()
            volatility_ratio = recent_atr / long_term_atr if long_term_atr > 0 else 1.0
            
            if volatility_ratio > 1.5:
                return "HIGH_VOLATILITY"
            elif volatility_ratio < 0.7:
                return "LOW_VOLATILITY"
        
        # 추세 분석
        if market_trend == TrendType.BULLISH:
            return "BULL_MARKET"
        elif market_trend == TrendType.BEARISH:
            return "BEAR_MARKET"
        else:
            return "SIDEWAYS_MARKET"
    
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
        if self.current_strategy:
            return {
                "mode": "single",
                "strategy": {
                    "name": self.current_strategy.get_name(),
                    "type": self.current_strategy.strategy_type.value,
                    "threshold": self.current_strategy.config.signal_threshold,
                    "risk_per_trade": self.current_strategy.config.risk_per_trade
                }
            }
        elif self.current_mix_config:
            return {
                "mode": "mix",
                "mix_config": {
                    "mode": self.current_mix_config.mode.value,
                    "strategies": {st.value: w for st, w in self.current_mix_config.strategies.items()},
                    "threshold_adjustment": self.current_mix_config.threshold_adjustment
                }
            }
        else:
            return {"mode": "none", "strategy": None}
    
    def enable_auto_strategy_selection(self, enable: bool = True):
        """자동 전략 선택 활성화/비활성화"""
        self.auto_strategy_selection = enable
        logger.info(f"자동 전략 선택: {'활성화' if enable else '비활성화'}")
    
    def get_dynamic_strategy_info(self, strategy_name: str = None) -> Dict[str, Any]:
        """동적 전략 정보를 반환합니다."""
        if strategy_name:
            strategy = self.dynamic_strategies.get(strategy_name)
            if not strategy:
                return {"error": f"Dynamic strategy not found: {strategy_name}"}
        else:
            strategy = self.current_dynamic_strategy
            if not strategy:
                return {"error": "No current dynamic strategy"}
        
        info = {
            "strategy_name": strategy.strategy_name,
            "description": strategy.strategy_config.get("description", ""),
            "signal_threshold": strategy.strategy_config.get("signal_threshold", 0),
            "risk_per_trade": strategy.strategy_config.get("risk_per_trade", 0),
            "detectors": strategy.strategy_config.get("detectors", {}),
            "modifiers": strategy.strategy_config.get("modifiers", []),
            "modifier_count": len(strategy.modifier_engine.modifiers) if strategy.modifier_engine else 0,
            "is_current": strategy == self.current_dynamic_strategy
        }
        
        # 마지막 분석 결과가 있으면 추가
        if strategy.last_context:
            info["last_analysis"] = strategy.get_context_summary()
            
        return info
    
    def get_dynamic_strategy_detailed_log(self, strategy_name: str = None) -> List[Dict[str, Any]]:
        """동적 전략의 상세 분석 로그를 반환합니다."""
        if strategy_name:
            strategy = self.dynamic_strategies.get(strategy_name)
        else:
            strategy = self.current_dynamic_strategy
            
        if not strategy:
            return []
            
        return strategy.get_detailed_log()
    
    def list_dynamic_strategies(self) -> List[str]:
        """사용 가능한 동적 전략 목록을 반환합니다."""
        return list(self.dynamic_strategies.keys())
    
    def enable_dynamic_strategies(self, enable: bool = True):
        """동적 전략 시스템 활성화/비활성화"""
        self.enable_dynamic_strategies = enable
        logger.info(f"동적 전략 시스템: {'활성화' if enable else '비활성화'}")
        
        if enable and not self.dynamic_strategies:
            # 동적 전략이 없으면 초기화 시도
            self._initialize_dynamic_strategies() 