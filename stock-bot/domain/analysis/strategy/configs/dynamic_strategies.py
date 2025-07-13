# ==============================================================================
# 동적 가중치 조절 시스템 설정 (v3)
# 거시 경제 상황에 따라 기술적 지표의 가중치를 동적으로 변경하는 지능형 시스템
# ==============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ModifierActionType(Enum):
    """모디파이어 액션 타입"""
    VETO_BUY = "VETO_BUY"           # 매수 신호 거부
    VETO_SELL = "VETO_SELL"         # 매도 신호 거부
    VETO_ALL = "VETO_ALL"           # 모든 신호 거부
    ADJUST_WEIGHTS = "ADJUST_WEIGHTS" # 가중치 조정
    ADJUST_SCORE = "ADJUST_SCORE"    # 점수 보정
    ADJUST_THRESHOLD = "ADJUST_THRESHOLD" # 임계값 조정


@dataclass
class ModifierCondition:
    """모디파이어 조건"""
    operator: str  # ">", "<", ">=", "<=", "==", "!=", "is_above", "is_below"
    value: Optional[float] = None
    reference: Optional[str] = None  # 비교 대상 (예: "sma_200")


@dataclass
class ModifierAction:
    """모디파이어 액션"""
    type: ModifierActionType
    adjustments: Optional[Dict[str, float]] = None  # 가중치 조정값
    multiplier: Optional[float] = None              # 점수 배율
    threshold_adjustment: Optional[float] = None    # 임계값 조정
    reason: Optional[str] = None                    # 액션 이유


@dataclass
class ModifierDefinition:
    """모디파이어 정의"""
    description: str
    detector: str  # 사용할 거시 지표 detector
    condition: ModifierCondition
    action: ModifierAction
    priority: int = 100  # 낮을수록 먼저 실행
    enabled: bool = True


# ==============================================================================
# 모디파이어(Modifier) 정의: 시장 상황에 따라 전략의 파라미터를 동적으로 변경하는 규칙들
# ==============================================================================
MODIFIER_DEFINITIONS = {
    # --- 기존 필터는 'VETO' 액션을 가진 모디파이어로 재정의 ---
    "vix_filter": ModifierDefinition(
        description="VIX 지수가 30을 초과하면 위험 회피 모드로 간주하여 매수 신호 거부",
        detector="vix",
        condition=ModifierCondition(operator=">", value=30),
        action=ModifierAction(type=ModifierActionType.VETO_BUY, reason="High VIX volatility"),
        priority=10  # 높은 우선순위
    ),

    "extreme_fear_filter": ModifierDefinition(
        description="VIX 지수가 35를 초과하면 극도의 공포 상태로 모든 거래 중단",
        detector="vix",
        condition=ModifierCondition(operator=">", value=35),
        action=ModifierAction(type=ModifierActionType.VETO_ALL, reason="Extreme market fear"),
        priority=5  # 최고 우선순위
    ),

    # --- 새로운 동적 가중치 조절 규칙 ---
    "vix_high_volatility_mode": ModifierDefinition(
        description="VIX가 25를 넘으면 변동성 장세로 판단, RSI 가중치 증가, MACD 가중치 감소",
        detector="vix",
        condition=ModifierCondition(operator=">", value=25),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_WEIGHTS,
            adjustments={
                "rsi": 0.2,   # RSI 가중치 +0.2 증가
                "macd": -0.2  # MACD 가중치 -0.2 감소
            },
            reason="High volatility environment favors momentum indicators"
        ),
        priority=50
    ),

    "market_in_uptrend": ModifierDefinition(
        description="S&P 500 지수가 200일선 위에 있으면 상승장으로 판단, 추세 추종 지표 가중치 증가",
        detector="sp500_sma_200",
        condition=ModifierCondition(operator="is_above"),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_WEIGHTS,
            adjustments={
                "macd": 0.15,
                "sma": 0.15,
                "adx": 0.1
            },
            reason="Bull market environment favors trend-following indicators"
        ),
        priority=60
    ),

    "market_in_downtrend": ModifierDefinition(
        description="S&P 500 지수가 200일선 아래에 있으면 하락장으로 판단, 역추세 지표 가중치 증가",
        detector="sp500_sma_200",
        condition=ModifierCondition(operator="is_below"),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_WEIGHTS,
            adjustments={
                "rsi": 0.25,     # 과매도 상태에서 반등 포착
                "stoch": 0.15,   # 스토캐스틱으로 단기 반전 포착
                "macd": -0.15,   # 추세 추종 지표 비중 감소
                "sma": -0.1
            },
            reason="Bear market environment favors mean-reversion indicators"
        ),
        priority=60
    ),

    "low_volatility_consolidation": ModifierDefinition(
        description="VIX가 15 이하로 낮으면 횡보장으로 판단, 모든 신호 임계값 상향 조정",
        detector="vix",
        condition=ModifierCondition(operator="<", value=15),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_THRESHOLD,
            threshold_adjustment=2.0,  # 임계값 +2점 상향
            reason="Low volatility environment requires stronger signals"
        ),
        priority=70
    ),

    "fear_greed_extreme_greed": ModifierDefinition(
        description="공포탐욕지수가 80 이상이면 극도의 탐욕 상태로 매수 신호 억제",
        detector="fear_greed_index",
        condition=ModifierCondition(operator=">=", value=80),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_SCORE,
            multiplier=0.6,  # 매수 점수 40% 감소
            reason="Extreme greed suggests market top"
        ),
        priority=30
    ),

    "fear_greed_extreme_fear": ModifierDefinition(
        description="공포탐욕지수가 20 이하면 극도의 공포 상태로 매수 신호 강화",
        detector="fear_greed_index",
        condition=ModifierCondition(operator="<=", value=20),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_SCORE,
            multiplier=1.3,  # 매수 점수 30% 증가
            reason="Extreme fear suggests buying opportunity"
        ),
        priority=30
    ),

    "dollar_strength_mode": ModifierDefinition(
        description="달러 지수(DXY)가 105를 넘으면 달러 강세로 판단, 글로벌 주식 투자 신중",
        detector="dxy",
        condition=ModifierCondition(operator=">", value=105),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_SCORE,
            multiplier=0.8,  # 전체 점수 20% 감소
            reason="Strong dollar headwind for equity markets"
        ),
        priority=40
    ),

    "yield_curve_inversion": ModifierDefinition(
        description="10년 국채 수익률이 4.5%를 넘으면 고금리 환경으로 성장주 비중 감소",
        detector="us_10y_treasury_yield",
        condition=ModifierCondition(operator=">", value=4.5),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_SCORE,
            multiplier=0.85,  # 전체 점수 15% 감소
            reason="High yield environment challenges growth stocks"
        ),
        priority=40
    )
}


# ==============================================================================
# 전략 정의: 기본 가중치와 적용할 모디파이어를 설정
# ==============================================================================
STRATEGY_DEFINITIONS = {
    "dynamic_weight_strategy": {
        "description": "거시 상황에 따라 기술적 지표의 가중치가 동적으로 변하는 전략",
        "signal_threshold": 8.0,  # 기본 임계값
        "risk_per_trade": 0.02,
        "detectors": {
            # 각 detector의 기본 가중치를 정의
            "rsi": {"weight": 0.3},
            "macd": {"weight": 0.3},
            "sma": {"weight": 0.2},
            "stoch": {"weight": 0.15},
            "adx": {"weight": 0.05}
        },
        # 이 전략이 사용할 모디파이어들을 우선순위 순서로 나열
        "modifiers": [
            "extreme_fear_filter",     # priority 5
            "vix_filter",              # priority 10  
            "fear_greed_extreme_greed", # priority 30
            "fear_greed_extreme_fear",  # priority 30
            "dollar_strength_mode",     # priority 40
            "yield_curve_inversion",    # priority 40
            "vix_high_volatility_mode", # priority 50
            "market_in_uptrend",        # priority 60
            "market_in_downtrend",      # priority 60
            "low_volatility_consolidation" # priority 70
        ]
    }
}


# ==============================================================================
# 거시 지표 detector 매핑
# ==============================================================================
MACRO_DETECTOR_MAPPING = {
    "vix": "VIXDetector",
    "sp500_sma_200": "SP500SMADetector", 
    "fear_greed_index": "FearGreedDetector",
    "dxy": "DXYDetector",
    "us_10y_treasury_yield": "US10YTreasuryDetector",
    "buffett_indicator": "BuffettIndicatorDetector",
    "put_call_ratio": "PutCallRatioDetector"
}


def get_modifier_definition(modifier_name: str) -> Optional[ModifierDefinition]:
    """모디파이어 정의 조회"""
    return MODIFIER_DEFINITIONS.get(modifier_name)


def get_strategy_definition(strategy_name: str) -> Optional[Dict[str, Any]]:
    """전략 정의 조회 (이름 정규화 기능 추가)"""
    # 1. 소문자로 변환하고 하이픈을 밑줄로 변경
    normalized_name = strategy_name.lower().replace('-', '_')

    # 2. 정규화된 이름으로 직접 매칭 시도
    if normalized_name in STRATEGY_DEFINITIONS:
        return STRATEGY_DEFINITIONS[normalized_name]

    # 3. '_strategy' 접미사를 붙여서 다시 시도
    name_with_suffix = f"{normalized_name}_strategy"
    if name_with_suffix in STRATEGY_DEFINITIONS:
        return STRATEGY_DEFINITIONS[name_with_suffix]

    return None


def get_all_modifiers() -> Dict[str, ModifierDefinition]:
    """모든 모디파이어 정의 반환"""
    return MODIFIER_DEFINITIONS.copy()


def get_all_strategies() -> Dict[str, Dict[str, Any]]:
    """모든 전략 정의 반환"""
    return STRATEGY_DEFINITIONS.copy() 