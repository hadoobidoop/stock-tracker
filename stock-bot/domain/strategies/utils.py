"""
전략 관련 유틸리티 함수들 (하위 호환성용)

중요: 이 모듈의 함수들은 하위 호환성을 위해 유지되지만,
새로운 코드에서는 strategy_registry를 직접 사용하는 것을 권장합니다.
"""

from typing import List


def get_available_static_strategies() -> List[str]:
    """
    사용 가능한 정적 전략 목록을 반환합니다.
    
    Note: 하위 호환성을 위해 유지. 새 코드에서는 
    strategy_registry.get_available_strategies("static") 사용 권장.
    
    Returns:
        List[str]: 정적 전략 이름들의 리스트
    """
    try:
        from domain.orchestration.strategy_registry import strategy_registry
        return strategy_registry.get_available_strategies("static")["static"]
    except ImportError:
        # 폴백: 기본 전략들
        return ['conservative', 'balanced', 'aggressive', 'momentum', 'trend_following', 'scalping']