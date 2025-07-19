# 동적 전략 시스템(Dynamic Strategy System) 문서

---

## 1. 시스템 개요

동적 전략 시스템은 시장 환경, 거시지표, 실시간 데이터 등에 따라 **기술적 지표의 가중치, 신호 임계값, 전략 구성**을 동적으로 변경하는 지능형 트레이딩 전략 프레임워크입니다.

- **정적 전략**: 고정된 룰/가중치/임계값으로만 동작
- **동적 전략**: 거시지표, 시장상황, 외부 신호 등에 따라 실시간으로 전략 파라미터가 변화
- **활용 예시**: VIX 급등 시 매수 신호 차단, S&P 500 상승장 시 추세추종 가중치 강화, 공포탐욕지수 극단값에서 신호 조정 등

---

## 2. 주요 구성요소 및 클래스 구조

### 2.1 DynamicStrategyManager
- 동적 전략의 생성, 관리, 실행, 전환, 정보 조회, 로그 제공 등 핵심 매니저
- 주요 메서드: `initialize()`, `switch_strategy()`, `get_strategy_info()`, `get_detailed_log()`, `list_strategies()`, `enable()`
- 위치: `domain/strategies/dynamic/dynamic_strategy_manager.py`

### 2.2 DynamicCompositeStrategy
- 실제 동적 가중치 조절 전략의 본체(분석, 점수계산, 모디파이어 적용, 신호 생성)
- 기술적 지표 detector, DecisionContext, ModifierEngine 등과 연동
- 위치: `domain/strategies/dynamic/dynamic_strategy.py`

### 2.3 Modifier(모디파이어)
- 시장지표/거시지표/상황에 따라 전략 파라미터(가중치, 임계값, 점수 등)를 동적으로 조정하는 규칙 객체
- BaseModifier(추상클래스), MarketIndicatorModifier(대표 구현체) 등
- 위치: `domain/strategies/dynamic/modifiers/`

### 2.4 Config 구조
- 동적 전략 정의, 모디파이어 정의, 액션/조건/우선순위 등 모든 설정을 코드로 관리
- 위치: `domain/strategies/dynamic/configs/dynamic.py`

---

## 3. 동작 흐름 및 구조도

```mermaid
graph TD;
    A[시작/초기화] --> B[DynamicStrategyManager.initialize()]
    B --> C[config에서 모든 동적 전략 정의 로드]
    C --> D[각 전략별 DynamicCompositeStrategy 인스턴스 생성]
    D --> E[각 전략별 ModifierEngine/모디파이어 주입]
    E --> F[기본 전략 활성화]
    F --> G[analyze() 호출 시]
    G --> H[DecisionContext 생성]
    H --> I[기술적 지표 점수 계산]
    I --> J[모디파이어 조건/액션 적용]
    J --> K[최종 점수/신호 생성]
```

---

## 4. Config/설정 구조 예시

### 4.1 전략 정의 예시
```python
STRATEGY_DEFINITIONS = {
    "dynamic_weight_strategy": {
        "description": "거시 상황에 따라 기술적 지표의 가중치가 동적으로 변하는 전략",
        "signal_threshold": 8.0,
        "risk_per_trade": 0.02,
        "detectors": {
            "rsi": {"weight": 0.3},
            "macd": {"weight": 0.3},
            "sma": {"weight": 0.2},
            "stoch": {"weight": 0.15},
            "adx": {"weight": 0.05}
        },
        "modifiers": [
            "extreme_fear_filter",
            "vix_filter",
            "vix_high_volatility_mode",
            ...
        ]
    },
    ...
}
```

### 4.2 모디파이어 정의 예시
```python
MODIFIER_DEFINITIONS = {
    "vix_filter": ModifierDefinition(
        description="VIX 지수가 30을 초과하면 매수 신호 거부",
        detector="vix",
        condition=ModifierCondition(operator=">", value=30),
        action=ModifierAction(type=ModifierActionType.VETO_BUY, reason="High VIX volatility"),
        priority=10
    ),
    ...
}
```

---

## 5. 주요 확장/사용법

- **새 동적 전략 추가**: `dynamic.py`에 전략 정의 추가 → 매니저에서 자동 인식/초기화
- **새 모디파이어 추가**: `MODIFIER_DEFINITIONS`에 규칙 추가, 필요시 커스텀 Modifier 클래스 구현
- **실행/전환**: `DynamicStrategyManager.switch_strategy('전략명')`으로 런타임에 전략 교체 가능
- **상세 로그/분석**: `get_strategy_info()`, `get_detailed_log()` 등으로 분석 근거/적용 내역 확인
- **실시간/백테스트/자동화**: SignalDetectionService 등에서 동적 전략을 통합적으로 활용 가능

---

## 6. 활용 포인트 및 참고

- **시장 변화에 유연하게 대응**: 단일 룰 기반 전략의 한계를 극복, 거시/심리/시장상황 반영
- **설명력/디버깅 용이**: 모든 판단/가중치/신호 근거가 DecisionContext/로그로 남음
- **확장성**: 새로운 지표, 모디파이어, 전략을 코드/설정만으로 손쉽게 추가 가능
- **참고 경로**:
    - 매니저: `domain/strategies/dynamic/dynamic_strategy_manager.py`
    - 전략: `domain/strategies/dynamic/dynamic_strategy.py`
    - 모디파이어: `domain/strategies/dynamic/modifiers/`
    - 설정: `domain/strategies/dynamic/configs/dynamic.py`

---

## 7. 예시 코드 스니펫

```python
# 동적 전략 매니저 초기화 및 사용 예시
from domain.strategies.dynamic.dynamic_strategy_manager import DynamicStrategyManager

manager = DynamicStrategyManager()
manager.initialize()

# 전략 전환
manager.switch_strategy('dynamic_weight_strategy')

# 현재 전략 정보/상세 로그 조회
info = manager.get_strategy_info()
log = manager.get_detailed_log()

# 전략 리스트
print(manager.list_strategies())
``` 