"""
전략 매니저 - 여러 전략을 관리하고 동적으로 교체할 수 있는 시스템

이 모듈은 사용자가 원하는 "갈아끼우며 사용할 수 있는" 전략 시스템을 제공합니다.
"""

from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
from dataclasses import asdict

from infrastructure.db.models.enums import TrendType
from domain.analysis.config.strategy_settings import (
    StrategyType, StrategyConfig, STRATEGY_CONFIGS, 
    StrategyMixMode, StrategyMixConfig, STRATEGY_MIXES,
    MARKET_CONDITION_STRATEGIES
)
from .base_strategy import BaseStrategy, StrategyResult
from .strategy_implementations import StrategyFactory
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
        self.current_strategy: Optional[BaseStrategy] = None
        self.current_mix_config: Optional[StrategyMixConfig] = None
        self.performance_history: List[Dict] = []
        
        # 지표 캐시 (모든 전략이 공유)
        self.indicator_cache: Dict[str, Dict] = {}
        self.cache_last_updated: Dict[str, datetime] = {}
        
        # 설정
        self.auto_strategy_selection = False
        self.market_condition_detection = True
        
    def initialize_strategies(self, strategy_types: List[StrategyType] = None) -> bool:
        """전략들을 초기화합니다."""
        if strategy_types is None:
            # 기본적으로 모든 전략 로드
            strategy_types = [
                StrategyType.CONSERVATIVE,
                StrategyType.BALANCED,
                StrategyType.AGGRESSIVE,
                StrategyType.MOMENTUM,
                StrategyType.TREND_FOLLOWING,
                StrategyType.CONTRARIAN,
                StrategyType.SCALPING,
                StrategyType.SWING,
                # 새로 추가된 전략 포함
                StrategyType.MEAN_REVERSION,
                StrategyType.TREND_PULLBACK,
                StrategyType.VOLATILITY_BREAKOUT,
                StrategyType.QUALITY_TREND,
                StrategyType.MULTI_TIMEFRAME,
            ]
        
        logger.info(f"전략 초기화 시작: {len(strategy_types)}개 전략")
        
        success_count = 0
        for strategy_type in strategy_types:
            try:
                config = STRATEGY_CONFIGS.get(strategy_type)
                if not config:
                    logger.warning(f"전략 설정을 찾을 수 없음: {strategy_type}")
                    continue
                
                strategy = StrategyFactory.create_strategy(strategy_type, config)
                
                if strategy.initialize():
                    self.active_strategies[strategy_type] = strategy
                    success_count += 1
                    logger.info(f"전략 초기화 성공: {strategy.get_name()}")
                else:
                    logger.error(f"전략 초기화 실패: {strategy.get_name()}")
                
            except Exception as e:
                logger.error(f"전략 초기화 실패 {strategy_type}: {e}")
                continue
        
        # 기본 전략 설정
        if StrategyType.BALANCED in self.active_strategies:
            self.current_strategy = self.active_strategies[StrategyType.BALANCED]
        elif self.active_strategies:
            self.current_strategy = list(self.active_strategies.values())[0]
        
        logger.info(f"전략 초기화 완료: {success_count}/{len(strategy_types)} 성공")
        if self.current_strategy:
            logger.info(f"기본 전략 설정: {self.current_strategy.get_name()}")
        
        return success_count > 0
    
    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """전략을 교체합니다."""
        if strategy_type not in self.active_strategies:
            logger.warning(f"활성화되지 않은 전략: {strategy_type}")
            return False
        
        old_strategy = self.current_strategy.get_name() if self.current_strategy else "None"
        self.current_strategy = self.active_strategies[strategy_type]
        self.current_mix_config = None  # 단일 전략 모드
        
        logger.info(f"전략 교체: {old_strategy} -> {self.current_strategy.get_name()}")
        return True
    
    def set_strategy_mix(self, mix_name: str = None, custom_mix: StrategyMixConfig = None) -> bool:
        """전략 조합을 설정합니다."""
        mix_config = None
        
        if custom_mix:
            mix_config = custom_mix
        elif mix_name and mix_name in STRATEGY_MIXES:
            mix_config = STRATEGY_MIXES[mix_name]
        else:
            logger.warning(f"알 수 없는 전략 조합: {mix_name}")
            return False
        
        # 필요한 전략들이 활성화되어 있는지 확인
        missing_strategies = []
        for strategy_type in mix_config.strategies.keys():
            if strategy_type not in self.active_strategies:
                missing_strategies.append(strategy_type)
        
        if missing_strategies:
            logger.warning(f"전략 조합에 필요한 전략이 비활성화됨: {missing_strategies}")
            return False
        
        self.current_mix_config = mix_config
        self.current_strategy = None  # 조합 모드
        
        logger.info(f"전략 조합 설정: {mix_name or 'custom'}")
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
        
        # 단일 전략 모드
        if self.current_strategy and not self.current_mix_config:
            return self.current_strategy.analyze(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
            )
        
        # 전략 조합 모드
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
        """모든 활성화된 전략으로 분석합니다."""
        results = {}
        
        for strategy_type, strategy in self.active_strategies.items():
            try:
                result = strategy.analyze(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
                )
                results[strategy_type] = result
            except Exception as e:
                logger.error(f"전략 분석 실패 {strategy.get_name()}: {e}")
                continue
        
        return results
    
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
            i: (result, weight) for i, (result, weight) in enumerate(high_confidence_results)
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
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """사용 가능한 전략 목록을 반환합니다."""
        strategies = []
        
        for strategy_type, strategy in self.active_strategies.items():
            strategies.append({
                "type": strategy_type.value,
                "name": strategy.get_name(),
                "description": strategy.config.description,
                "threshold": strategy.config.signal_threshold,
                "risk_per_trade": strategy.config.risk_per_trade,
                "is_current": strategy == self.current_strategy
            })
        
        return strategies 