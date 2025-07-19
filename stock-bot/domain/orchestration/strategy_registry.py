"""
중앙화된 전략 레지스트리 - 모든 전략 관련 정보를 통합 관리
"""

from typing import Dict, List, Optional, Tuple, Any

from domain.signals.models.enums import StrategyType, StrategyMode
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class StrategyRegistry:
    """중앙화된 전략 레지스트리"""
    
    def __init__(self):
        self._static_strategies: Dict[StrategyType, Dict[str, Any]] = {}
        self._dynamic_strategies: Dict[str, Dict[str, Any]] = {}
        self._strategy_mixes: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def initialize(self):
        """레지스트리 초기화"""
        if self._initialized:
            return
            
        self._load_static_strategies()
        self._load_dynamic_strategies()
        self._load_strategy_mixes()
        self._initialized = True
        
        logger.info(f"StrategyRegistry 초기화 완료: {len(self._static_strategies)} 정적, "
                   f"{len(self._dynamic_strategies)} 동적, {len(self._strategy_mixes)} 조합")
    
    def _load_static_strategies(self):
        """정적 전략 로드"""
        from domain.orchestration.factory import STRATEGY_CLASS_MAP
        
        for strategy_type in StrategyType:
            if strategy_type in STRATEGY_CLASS_MAP:
                self._static_strategies[strategy_type] = {
                    "class": STRATEGY_CLASS_MAP[strategy_type],
                    "type": strategy_type,
                    "available": True
                }
    
    def _load_dynamic_strategies(self):
        """동적 전략 로드"""
        try:
            from domain.strategies.dynamic.dynamic_strategy_manager.configs.dynamic_strategies import get_all_strategies
            strategies = get_all_strategies()
            
            for name, config in strategies.items():
                self._dynamic_strategies[name] = {
                    "config": config,
                    "available": True
                }
        except ImportError as e:
            logger.warning(f"동적 전략 로드 실패: {e}")
    
    def _load_strategy_mixes(self):
        """전략 조합 로드"""
        try:
            from domain.strategies.mixes import STRATEGY_MIXES
            
            for name, config in STRATEGY_MIXES.items():
                self._strategy_mixes[name] = {
                    "config": config,
                    "available": True
                }
        except ImportError as e:
            logger.warning(f"전략 조합 로드 실패: {e}")
    
    def get_available_strategies(self, strategy_type: str = "all") -> Dict[str, List[str]]:
        """사용 가능한 전략 목록 조회"""
        self.initialize()
        
        result = {
            "static": [],
            "dynamic": [],
            "mix": []
        }
        
        if strategy_type in ["all", "static"]:
            result["static"] = [st.value for st in self._static_strategies.keys()]
        
        if strategy_type in ["all", "dynamic"]:
            result["dynamic"] = list(self._dynamic_strategies.keys())
        
        if strategy_type in ["all", "mix"]:
            result["mix"] = list(self._strategy_mixes.keys())
        
        return result
    
    def is_strategy_supported(self, strategy_identifier: str) -> Tuple[bool, str]:
        """전략 지원 여부 확인"""
        self.initialize()
        
        # 정적 전략 확인
        try:
            strategy_type = StrategyType(strategy_identifier.lower())
            if strategy_type in self._static_strategies:
                return True, "static"
        except ValueError:
            pass
        
        # 동적 전략 확인
        if strategy_identifier in self._dynamic_strategies:
            return True, "dynamic"
        
        # 전략 조합 확인
        if strategy_identifier in self._strategy_mixes:
            return True, "mix"
        
        return False, "none"
    
    def get_strategy_config(self, strategy_identifier: str, strategy_class: str = None) -> Optional[Dict[str, Any]]:
        """전략 설정 조회"""
        self.initialize()
        
        if strategy_class:
            return self._get_strategy_config_by_class(strategy_identifier, strategy_class)
        
        # 자동 감지
        is_supported, strategy_type = self.is_strategy_supported(strategy_identifier)
        if is_supported:
            return self._get_strategy_config_by_class(strategy_identifier, strategy_type)
        
        return None
    
    def _get_strategy_config_by_class(self, strategy_identifier: str, strategy_class: str) -> Optional[Dict[str, Any]]:
        """클래스별 전략 설정 조회"""
        if strategy_class == "static":
            try:
                strategy_type = StrategyType(strategy_identifier.lower())
                if strategy_type in self._static_strategies:
                    return {
                        "type": "static",
                        "strategy_type": strategy_type,
                        "available": True
                    }
            except ValueError:
                pass
        
        elif strategy_class == "dynamic":
            if strategy_identifier in self._dynamic_strategies:
                config = self._dynamic_strategies[strategy_identifier]["config"]
                return {
                    "type": "dynamic",
                    "strategy_name": strategy_identifier,
                    "config": config,
                    "available": True
                }
        
        elif strategy_class == "mix":
            if strategy_identifier in self._strategy_mixes:
                config = self._strategy_mixes[strategy_identifier]["config"]
                return {
                    "type": "mix",
                    "mix_name": strategy_identifier,
                    "config": config,
                    "available": True
                }
        
        return None
    
    def get_recommended_strategy(self, market_condition: str) -> Optional[Tuple[str, str]]:
        """시장 상황에 따른 전략 추천"""
        try:
            from domain.strategies.mixes import MARKET_CONDITION_STRATEGIES
            condition_strategies = MARKET_CONDITION_STRATEGIES.get(market_condition, {})
            
            for priority in ["primary", "secondary", "fallback"]:
                strategy_info = condition_strategies.get(priority)
                if strategy_info and self.is_strategy_supported(strategy_info)[0]:
                    return strategy_info, "static"  # 기본적으로 정적 전략으로 가정
            
        except ImportError:
            logger.warning(f"시장 상황 '{market_condition}'에 대한 추천 전략을 찾지 못했습니다.")
        
        return None


# 전역 인스턴스
strategy_registry = StrategyRegistry()


 