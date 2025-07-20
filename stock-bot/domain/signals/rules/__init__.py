"""
Rules Package

모든 거래 규칙들을 통합하여 하나의 RULES 딕셔너리로 제공합니다.
각 분야별 규칙 모듈(momentum, trend, volume, volatility)의 규칙들을 통합합니다.

사용 예시:
```python
from domain.signals.rules import RULES

# 특정 규칙 사용
if RULES['macd_confirms_golden_cross'](data):
    print("MACD 골든크로스 확인됨")

# 여러 규칙 조합
bullish_momentum = RULES['strong_bullish_momentum_consensus'](data)
volume_surge = RULES['volume_surge_pattern'](data)
if bullish_momentum and volume_surge:
    print("강한 매수 신호")
```
"""

from .momentum import MOMENTUM_RULES
from .trend import TREND_RULES
from .volume import VOLUME_RULES
from .volatility import VOLATILITY_RULES

# 모든 규칙을 통합한 단일 딕셔너리
RULES = {
    **MOMENTUM_RULES,
    **TREND_RULES,
    **VOLUME_RULES,
    **VOLATILITY_RULES,
}

# 규칙 카테고리별 접근을 위한 별도 export
__all__ = [
    'RULES',
    'MOMENTUM_RULES',
    'TREND_RULES', 
    'VOLUME_RULES',
    'VOLATILITY_RULES'
]

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