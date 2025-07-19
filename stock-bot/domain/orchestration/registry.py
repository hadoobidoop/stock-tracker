from typing import List

def get_available_static_strategies() -> List[str]:
    """동적으로 사용 가능한 정적 전략 목록 조회"""
    try:
        from domain.signals.strategy.strategy_factory import StrategyFactory
        return [st.value.upper() for st in StrategyFactory.get_available_static_strategies()]
    except ImportError:
        # 폴백: 기본 전략들만
        return ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]


def get_available_dynamic() -> List[str]:
    """동적으로 사용 가능한 동적 전략 목록 조회"""
    try:
        from domain.strategies.dynamic.dynamic_strategy_manager.configs.dynamic import get_all_strategies
        return list(get_all_strategies().keys())
    except ImportError:
        # 폴백: 기본 동적 전략들만
        return ["dynamic_weight_strategy", "aggressive_dynamic_strategy"]


def get_available_strategy_mix() -> List[str]:
    """사용 가능한 Strategy Mix 목록 조회"""
    return ["balanced_mix", "conservative_mix", "aggressive_mix"] 