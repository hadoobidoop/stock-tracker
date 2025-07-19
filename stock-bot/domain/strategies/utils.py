"""
전략 관련 유틸리티 함수들
"""

from typing import List


def get_available_static_strategies() -> List[str]:
    """
    사용 가능한 정적 전략 목록을 반환합니다.
    
    Returns:
        List[str]: 정적 전략 이름들의 리스트
    """
    # strategy_registry를 사용하여 정적 전략 목록 가져오기
    try:
        from domain.orchestration.strategy_registry import strategy_registry
        available = strategy_registry.get_available_strategies("static")
        return available["static"]
    except ImportError:
        # 폴백: 기본 전략들
        return ['conservative', 'balanced', 'aggressive', 'momentum', 'trend_following', 'scalping']


def get_available_dynamic_strategies() -> List[str]:
    """
    사용 가능한 동적 전략 목록을 반환합니다.
    
    Returns:
        List[str]: 동적 전략 이름들의 리스트
    """
    try:
        from domain.orchestration.strategy_registry import strategy_registry
        available = strategy_registry.get_available_strategies("dynamic")
        return available["dynamic"]
    except ImportError:
        # 폴백: 기본 동적 전략들
        return ['dynamic_weight_strategy', 'adaptive_momentum_hybrid', 'conservative_reversion_hybrid']


def get_available_strategy_mixes() -> List[str]:
    """
    사용 가능한 전략 믹스 목록을 반환합니다.
    
    Returns:
        List[str]: 전략 믹스 이름들의 리스트
    """
    try:
        from domain.orchestration.strategy_registry import strategy_registry
        available = strategy_registry.get_available_strategies("mix")
        return available["mix"]
    except ImportError:
        # 폴백: 기본 믹스들
        return ['balanced_mix', 'conservative_mix', 'aggressive_mix']


def get_all_available_strategies() -> dict:
    """
    모든 사용 가능한 전략들을 카테고리별로 반환합니다.
    
    Returns:
        dict: 전략 카테고리별 목록
    """
    return {
        'static': get_available_static_strategies(),
        'dynamic': get_available_dynamic_strategies(),
        'mix': get_available_strategy_mixes()
    }