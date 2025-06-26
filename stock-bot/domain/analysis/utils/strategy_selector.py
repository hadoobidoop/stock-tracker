"""
전략 선택 및 관리 유틸리티

설정 기반으로 정적/동적/Static Strategy Mix 전략을 유연하게 선택하고 관리
"""

from typing import Dict, Any, Optional, List, Union
from enum import Enum
import os
from functools import lru_cache

from common.config.settings import (
    StrategyMode, DefaultStrategyConfig, EnvironmentConfig, get_strategy_availability
)
from domain.analysis.config.static_strategies import StrategyType, get_strategy_config, get_static_strategy_types
from domain.analysis.config.dynamic_strategies import STRATEGY_DEFINITIONS
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StrategySelector:
    """전략 선택 및 관리 클래스"""
    
    def __init__(self):
        self.current_mode: StrategyMode = EnvironmentConfig.get_strategy_mode()
        self.fallback_enabled = DefaultStrategyConfig.SCHEDULER_STRATEGY_FALLBACK_ENABLED
        # 캐시는 인스턴스별로 관리
        self._available_strategies_cache = None
        
    @lru_cache(maxsize=1)
    def _load_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 전략들 로드 (캐싱 적용)"""
        strategies = {
            "static": {},
            "dynamic": {},
            "static_mix": {}
        }
        
        strategy_availability = get_strategy_availability()
        
        # 정적 전략 로드
        if strategy_availability["static_strategies"]["enabled"]:
            for strategy_type in get_static_strategy_types():
                if strategy_type != StrategyType.DYNAMIC_WEIGHT:  # 동적 전략 제외
                    config = get_strategy_config(strategy_type)
                    if config:
                        strategies["static"][strategy_type.value] = {
                            "config": config,
                            "type": strategy_type,
                            "available": True
                        }
        
        # 동적 전략 로드
        if strategy_availability["dynamic_strategies"]["enabled"]:
            for strategy_name, strategy_config in STRATEGY_DEFINITIONS.items():
                strategies["dynamic"][strategy_name] = {
                    "config": strategy_config,
                    "available": True
                }
        
        # Static Strategy Mix 로드
        if strategy_availability["strategy_mix"]["enabled"]:
            for mix_name in strategy_availability["strategy_mix"]["available"]:
                strategies["static_mix"][mix_name] = {
                    "available": True
                }
        
        return strategies
    
    @property
    def available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 전략들 (캐싱된 결과)"""
        return self._load_available_strategies()
    
    def get_default_strategy_config(self, mode: Optional[StrategyMode] = None) -> Dict[str, Any]:
        """기본 전략 설정 반환"""
        if mode is None:
            mode = self.current_mode
            
        config = {
            "mode": mode,
            "strategy_name": None,
            "config": None,
            "fallback": None
        }
        
        strategy_configs = {
            StrategyMode.STATIC: lambda: {
                "strategy_name": DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY,
                "config": self.get_static_strategy_config(DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY),
                "fallback": self._get_fallback_config()
            },
            StrategyMode.DYNAMIC: lambda: {
                "strategy_name": DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY,
                "config": self.get_dynamic_strategy_config(DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY),
                "fallback": self._get_fallback_config()
            },
            StrategyMode.STATIC_MIX: lambda: {
                "strategy_name": DefaultStrategyConfig.DEFAULT_STRATEGY_MIX,
                "config": self.get_strategy_mix_config(DefaultStrategyConfig.DEFAULT_STRATEGY_MIX),
                "fallback": self._get_fallback_config()
            }
        }
        
        mode_config = strategy_configs.get(mode, strategy_configs[StrategyMode.DYNAMIC])()
        config.update(mode_config)
        
        return config
    
    def get_static_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """정적 전략 설정 조회"""
        # 대소문자 구분 없이 검색
        strategy_name_normalized = strategy_name.upper()
        strategy_info = self.available_strategies["static"].get(strategy_name_normalized)
        
        # 만약 대문자로 찾을 수 없으면 소문자로도 시도
        if not strategy_info:
            strategy_name_normalized = strategy_name.lower()
            strategy_info = self.available_strategies["static"].get(strategy_name_normalized)
        
        if strategy_info and strategy_info["available"]:
            return {
                "type": "static",
                "strategy_type": strategy_info["type"],
                "config": strategy_info["config"],
                "name": strategy_info["config"].name,
                "description": strategy_info["config"].description
            }
        return None
    
    def get_dynamic_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """동적 전략 설정 조회"""
        strategy_info = self.available_strategies["dynamic"].get(strategy_name)
        if strategy_info and strategy_info["available"]:
            config = strategy_info["config"]
            return {
                "type": "dynamic",
                "strategy_name": strategy_name,
                "config": config,
                "name": strategy_name.replace('_', ' ').title(),
                "description": config.get("description", "동적 전략"),
                "signal_threshold": config.get("signal_threshold", 8.0),
                "risk_per_trade": config.get("risk_per_trade", 0.02)
            }
        return None
    
    def get_strategy_mix_config(self, mix_name: str) -> Optional[Dict[str, Any]]:
        """Static Strategy Mix 설정 조회"""
        strategy_info = self.available_strategies["static_mix"].get(mix_name)
        if strategy_info and strategy_info["available"]:
            return {
                "type": "static_mix",
                "mix_name": mix_name,
                "available": True,
                "name": f"{mix_name.replace('_', ' ').title()}",
                "description": f"정적 전략 조합: {mix_name}"
            }
        return None
    
    def _get_fallback_config(self) -> Optional[Dict[str, Any]]:
        """폴백 전략 설정"""
        if not self.fallback_enabled:
            return None
            
        fallback_strategy = DefaultStrategyConfig.SCHEDULER_FALLBACK_STATIC_STRATEGY
        return self.get_static_strategy_config(fallback_strategy)
    
    def get_realtime_strategy_config(self) -> Dict[str, Any]:
        """실시간 작업용 전략 설정"""
        env_config = EnvironmentConfig.get_realtime_strategy_config()
        mode = env_config["mode"]
        
        strategy_getters = {
            StrategyMode.STATIC: lambda: self.get_static_strategy_config(env_config["static_strategy"]),
            StrategyMode.DYNAMIC: lambda: self.get_dynamic_strategy_config(env_config["dynamic_strategy"]),
            StrategyMode.STATIC_MIX: lambda: self.get_strategy_mix_config(env_config["strategy_mix"])
        }
        
        strategy_config = strategy_getters.get(mode, lambda: self.get_default_strategy_config())()
        
        return {
            "mode": mode,
            "config": strategy_config,
            "fallback_enabled": env_config["fallback_enabled"],
            "fallback_config": self._get_fallback_config() if env_config["fallback_enabled"] else None
        }
    
    def list_available_strategies(self) -> Dict[str, List[Dict[str, Any]]]:
        """사용 가능한 모든 전략 목록"""
        result = {
            "static_strategies": [],
            "dynamic_strategies": [],
            "static_mix": []
        }
        
        # 정적 전략
        for name, info in self.available_strategies["static"].items():
            if info["available"]:
                result["static_strategies"].append({
                    "name": name,
                    "display_name": info["config"].name,
                    "description": info["config"].description,
                    "signal_threshold": info["config"].signal_threshold,
                    "risk_per_trade": info["config"].risk_per_trade
                })
        
        # 동적 전략
        for name, info in self.available_strategies["dynamic"].items():
            if info["available"]:
                config = info["config"]
                result["dynamic_strategies"].append({
                    "name": name,
                    "display_name": name.replace('_', ' ').title(),
                    "description": config.get("description", "동적 전략"),
                    "signal_threshold": config.get("signal_threshold", 8.0),
                    "risk_per_trade": config.get("risk_per_trade", 0.02),
                    "modifiers_count": len(config.get("modifiers", []))
                })
        
        # Static Strategy Mix
        for name, info in self.available_strategies["static_mix"].items():
            if info["available"]:
                result["static_mix"].append({
                    "name": name,
                    "display_name": f"{name.replace('_', ' ').title()}",
                    "description": f"정적 전략 조합: {name}"
                })
        
        return result
    
    def validate_strategy_selection(self, mode: StrategyMode, strategy_name: str) -> bool:
        """전략 선택 유효성 검증"""
        validation_map = {
            StrategyMode.STATIC: lambda name: name.upper() in self.available_strategies["static"],
            StrategyMode.DYNAMIC: lambda name: name in self.available_strategies["dynamic"],
            StrategyMode.STATIC_MIX: lambda name: name in self.available_strategies["static_mix"]
        }
        
        validator = validation_map.get(mode)
        return validator(strategy_name) if validator else False
    
    def get_strategy_by_name(self, strategy_name: str, strategy_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """이름으로 전략 조회 (타입 자동 감지)"""
        # 명시적 타입이 있으면 해당 타입에서만 검색
        if strategy_type:
            type_getters = {
                "static": self.get_static_strategy_config,
                "dynamic": self.get_dynamic_strategy_config,
                "static_mix": self.get_strategy_mix_config
            }
            getter = type_getters.get(strategy_type)
            return getter(strategy_name) if getter else None
        
        # 타입이 없으면 모든 타입에서 검색
        for search_method in [self.get_static_strategy_config, self.get_dynamic_strategy_config, self.get_strategy_mix_config]:
            result = search_method(strategy_name)
            if result:
                return result
        
        return None
    
    def set_current_mode(self, mode: StrategyMode):
        """현재 전략 모드 설정"""
        self.current_mode = mode
        # 캐시 초기화
        self._load_available_strategies.cache_clear()
        logger.info(f"전략 모드 변경: {mode.value}")
    
    def get_recommended_strategy(self, market_condition: Optional[str] = None) -> Dict[str, Any]:
        """시장 상황에 따른 추천 전략"""
        recommendations = {
            "high_volatility": lambda: self.get_static_strategy_config("CONSERVATIVE"),
            "bull_market": lambda: self.get_dynamic_strategy_config("aggressive_dynamic_strategy"),
            "bear_market": lambda: self.get_static_strategy_config("CONTRARIAN")
        }
        
        recommender = recommendations.get(market_condition)
        if recommender:
            result = recommender()
            if result:
                return result
        
        # 기본 추천: 동적 전략
        return self.get_dynamic_strategy_config(DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY)
    
    def refresh_available_strategies(self):
        """사용 가능한 전략 목록 갱신"""
        self._load_available_strategies.cache_clear()
        logger.info("전략 목록 캐시가 갱신되었습니다.")


# 전역 인스턴스 생성
strategy_selector = StrategySelector()


def get_current_strategy_config() -> Dict[str, Any]:
    """현재 전략 설정 반환"""
    return strategy_selector.get_realtime_strategy_config()


def list_all_strategies() -> Dict[str, List[Dict[str, Any]]]:
    """모든 사용 가능한 전략 목록"""
    return strategy_selector.list_available_strategies()


def select_strategy_by_name(strategy_name: str, strategy_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """이름으로 전략 선택"""
    return strategy_selector.get_strategy_by_name(strategy_name, strategy_type)


def is_strategy_supported(strategy_name: str, strategy_mode: Optional[StrategyMode] = None) -> bool:
    """전략 지원 여부 확인"""
    if strategy_mode:
        return strategy_selector.validate_strategy_selection(strategy_mode, strategy_name)
    
    # 모든 모드에서 확인
    for mode in StrategyMode:
        if strategy_selector.validate_strategy_selection(mode, strategy_name):
            return True
    return False 