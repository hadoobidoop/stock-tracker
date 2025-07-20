"""
Rules Package

재사용 가능한 규칙들을 파일별로 그룹화하고 하나의 RULES 딕셔너리로 통합합니다.
"""

from .momentum import MOMENTUM_RULES
from .trend import TREND_RULES
from .volatility import VOLATILITY_RULES
from .volume import VOLUME_RULES

# 모든 규칙을 통합한 딕셔너리
RULES = {
    **MOMENTUM_RULES,
    **TREND_RULES,
    **VOLUME_RULES,
    **VOLATILITY_RULES,
}

__all__ = ['RULES', 'MOMENTUM_RULES', 'TREND_RULES', 'VOLUME_RULES', 'VOLATILITY_RULES']

# 통합 규칙 개수 정보
RULE_COUNTS = {
    'momentum': len(MOMENTUM_RULES),
    'trend': len(TREND_RULES),
    'volume': len(VOLUME_RULES),
    'volatility': len(VOLATILITY_RULES),
    'total': len(RULES)
}

def get_rule_info():
    """
    등록된 규칙들의 정보를 반환합니다.
    
    Returns:
        Dict: 규칙 카테고리별 개수와 전체 개수
    """
    return RULE_COUNTS

def get_available_rules(category: str = None):
    """
    사용 가능한 규칙 목록을 반환합니다.
    
    Args:
        category: 특정 카테고리 ('momentum', 'trend', 'volume', 'volatility')
                 None이면 전체 규칙 반환
    
    Returns:
        List[str]: 규칙 이름 목록
    """
    if category == 'momentum':
        return list(MOMENTUM_RULES.keys())
    elif category == 'trend':
        return list(TREND_RULES.keys())
    elif category == 'volume':
        return list(VOLUME_RULES.keys())
    elif category == 'volatility':
        return list(VOLATILITY_RULES.keys())
    else:
        return list(RULES.keys())

def validate_rule_exists(rule_name: str) -> bool:
    """
    규칙이 존재하는지 확인합니다.
    
    Args:
        rule_name: 규칙 이름
    
    Returns:
        bool: 규칙 존재 여부
    """
    return rule_name in RULES 