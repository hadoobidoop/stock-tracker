"""
전략 선택 및 관리 유틸리티

설정 기반으로 정적/동적/Static Strategy Mix 전략을 유연하게 선택하고 관리
"""

from functools import lru_cache
from typing import Dict, Any, Optional, List, Union, Callable, Tuple

from domain.orchestration.config.environment import EnvironmentConfig
from domain.orchestration.factory import StrategyFactory
from domain.orchestration.strategy_registry import strategy_registry
from domain.signals.models.enums import StrategyType, StrategyMode
from domain.strategies.dynamic.dynamic_strategy_manager.configs.dynamic_strategies import STRATEGY_DEFINITIONS
from domain.strategies.mixes import MARKET_CONDITION_STRATEGIES
from domain.strategies.mixes.utils import get_strategy_mix_config as mixes_get_strategy_mix_config
from domain.strategies.strategy_config import get_strategy_availability, DefaultStrategyConfig
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
            # Use strategy_registry directly
            for strategy_name in strategy_registry.get_available_strategies("static")["static"]:
                strategy_type = StrategyType(strategy_name.lower())
                if strategy_type != StrategyType.DYNAMIC_WEIGHT:  # 동적 전략 제외
                    try:
                        strategy_instance = StrategyFactory.create_static_strategy(strategy_type)
                        if strategy_instance:
                            # YAML 전략인지 Python 전략인지 구분
                            if hasattr(strategy_instance, 'config') and hasattr(strategy_instance, 'strategy_name'):
                                # YAML 전략
                                strategies["static"][strategy_type.value] = {
                                    "config": strategy_instance.config,  # YAML config
                                    "strategy_instance": strategy_instance,
                                    "type": strategy_type,
                                    "available": True,
                                    "is_yaml": True
                                }
                            elif hasattr(strategy_instance, 'config'):
                                # Python 전략
                                strategies["static"][strategy_type.value] = {
                                    "config": strategy_instance.config,
                                    "strategy_instance": strategy_instance,
                                    "type": strategy_type,
                                    "available": True,
                                    "is_yaml": False
                                }
                    except Exception as e:
                        logger.warning(f"Failed to load strategy {strategy_type}: {e}")
        
        # 동적 전략 로드
        if strategy_availability["dynamic"]["enabled"]:
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
                "config": strategy_registry.get_strategy_config(DefaultStrategyConfig.DEFAULT_STATIC_STRATEGY, "static"),
                "fallback": self._get_fallback_config()
            },
            StrategyMode.DYNAMIC: lambda: {
                "strategy_name": DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY,
                "config": strategy_registry.get_strategy_config(DefaultStrategyConfig.DEFAULT_DYNAMIC_STRATEGY, "dynamic"),
                "fallback": self._get_fallback_config()
            },
            StrategyMode.STATIC_MIX: lambda: {
                "strategy_name": DefaultStrategyConfig.DEFAULT_STRATEGY_MIX,
                "config": mixes_get_strategy_mix_config(DefaultStrategyConfig.DEFAULT_STRATEGY_MIX),
                "fallback": self._get_fallback_config()
            }
        }
        
        mode_config = strategy_configs.get(mode, strategy_configs[StrategyMode.DYNAMIC])()
        config.update(mode_config)
        
        return config
    
    
    
    def _get_fallback_config(self) -> Optional[Dict[str, Any]]:
        """폴백 전략 설정"""
        if not self.fallback_enabled:
            return None
            
        fallback_strategy = DefaultStrategyConfig.SCHEDULER_FALLBACK_STATIC_STRATEGY
        return strategy_registry.get_strategy_config(fallback_strategy, "static")
    
    def get_realtime_strategy_config(self) -> Dict[str, Any]:
        """실시간 작업용 전략 설정"""
        env_config = EnvironmentConfig.get_realtime_strategy_config()
        mode = env_config["mode"]
        
        strategy_getters = {
            StrategyMode.STATIC: lambda: strategy_registry.get_strategy_config(env_config["static_strategy"], "static"),
            StrategyMode.DYNAMIC: lambda: strategy_registry.get_strategy_config(env_config["dynamic_strategy"], "dynamic"),
            StrategyMode.STATIC_MIX: lambda: mixes_get_strategy_mix_config(env_config["strategy_mix"])
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
            "dynamic": [],
            "static_mix": []
        }
        
        # 정적 전략
        for name, info in self.available_strategies["static"].items():
            if info["available"]:
                config = info["config"]
                is_yaml = info.get("is_yaml", False)
                
                # YAML 전략인지 Python 전략인지 구분
                if is_yaml:  # YAML 전략
                    display_name = config.strategy_info.get('name', name)
                    description = config.strategy_info.get('description', f"{name} 전략")
                    signal_threshold = config.signal_config.get('threshold', 8.0)
                    risk_per_trade = config.risk_management.get('risk_per_trade', 0.02)
                else:  # Python 전략
                    display_name = config.name if hasattr(config, 'name') else name
                    description = config.description if hasattr(config, 'description') else f"{name} 전략"
                    signal_threshold = config.signal_threshold if hasattr(config, 'signal_threshold') else 8.0
                    risk_per_trade = config.risk_per_trade if hasattr(config, 'risk_per_trade') else 0.02
                    
                result["static_strategies"].append({
                    "name": name,
                    "display_name": display_name,
                    "description": description,
                    "signal_threshold": signal_threshold,
                    "risk_per_trade": risk_per_trade
                })
        
        # 동적 전략
        for name, info in self.available_strategies["dynamic"].items():
            if info["available"]:
                config = info["config"]
                result["dynamic"].append({
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
            type_getters: Dict[str, Callable[[str], Optional[Dict[str, Any]]]] = {
                "static": lambda name: strategy_registry.get_strategy_config(name, "static"),
                "dynamic": lambda name: strategy_registry.get_strategy_config(name, "dynamic"),
                "static_mix": mixes_get_strategy_mix_config
            }
            getter = type_getters.get(strategy_type)
            return getter(strategy_name) if getter else None
        
        # 타입이 없으면 모든 타입에서 검색
        search_methods: List[Callable[[str], Optional[Dict[str, Any]]]] = [
            lambda name: strategy_registry.get_strategy_config(name, "static"),
            lambda name: strategy_registry.get_strategy_config(name, "dynamic"),
            mixes_get_strategy_mix_config
        ]
        for search_method in search_methods:
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
    
    def get_recommended_strategy(self, market_condition: str) -> Optional[Tuple[Union[StrategyType, str], str]]:
        """
        시장 상황에 가장 적합한 전략을 추천합니다.
        :param market_condition: 'BULL_MARKET', 'BEAR_MARKET' 등 시장 상황 문자열
        :return: (전략 타입/이름, 전략 클래스('static' 또는 'dynamic')) 튜플 또는 None
        """
        condition_strategies = MARKET_CONDITION_STRATEGIES.get(market_condition, {})
        
        for priority in ["primary", "secondary", "fallback"]:
            strategy_info = condition_strategies.get(priority)
            if not strategy_info:
                continue

            # strategy_info is a string (strategy name), not a dict
            strategy_id = strategy_info
            strategy_class = 'static'  # Assume strategy mix is static by default

            # 정적 전략인 경우, StrategyType Enum으로 변환 시도
            if strategy_class == 'static':
                try:
                    strategy_type_enum = StrategyType(strategy_id)
                    # 사용 가능한지 확인
                    if strategy_registry.get_strategy_config(strategy_type_enum.value, "static"):
                        return strategy_type_enum, 'static'
                except ValueError:
                    logger.warning(f"'{strategy_id}'는 유효한 StrategyType이 아닙니다.")
            
            # 동적 전략인 경우
            elif strategy_class == 'dynamic':
                # 사용 가능한지 확인
                if strategy_registry.get_strategy_config(strategy_id, "dynamic"):
                    return strategy_id, 'dynamic'

        logger.warning(f"'{market_condition}'에 대한 유효한 추천 전략을 찾지 못했습니다.")
        return None
    
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