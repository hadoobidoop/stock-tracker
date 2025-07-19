# Conservative Reversion Hybrid 전략 (보수적 평균 회귀 하이브리드)

---

## 1. 전략 개요

- **전략명:** Conservative Reversion Hybrid (보수적 평균 회귀 하이브리드)
- **폴더 구조:** `domain/strategies/conservative_reversion_hybrid/`
- **완전 독립 패키지:** 전략 본체가 폴더 내에서 독립적으로 관리됨
- **하위 전략 연동:** 하위 strategies 폴더(`conservative/`, `mean_reversion/`)의 정적 전략을 직접 import하여 인스턴스화
- **주요 신호:** 보수적 추세 확인(CONSERVATIVE) + 평균 회귀 진입(MEAN_REVERSION) 신호를 조합

---

## 2. 폴더/클래스 구조

```
domain/strategies/conservative_reversion_hybrid/
  conservative_reversion_hybrid_strategy.py      # 전략 본체
  configs/
    # (필요시 Detector/Config 분리)
  detectors/
    # (필요시 커스텀 Detector 래퍼)

# 하위 전략(연동)
domain/strategies/conservative/
  conservative_strategy.py
  ...
domain/strategies/mean_reversion/
  mean_reversion_strategy.py
  ...
```

---

## 3. 신호 생성 로직

- **하위 전략 연동:**
  - `conservative/`와 `mean_reversion/` 폴더의 전략을 직접 import하여 인스턴스화
  - 각 전략의 `analyze()` 결과를 조합(추세 동의 시 보너스, 반대 시 페널티)
- **장기추세 가중치:**
  - long_term_trend가 BULLISH면 buy_score 1.2배, BEARISH면 sell_score 1.2배
- **최종 신호:**
  - buy/sell 점수 중 높은 쪽이 임계값 이상이면 신호 발생
  - 두 전략의 신호 근거(signals_detected)도 모두 합산

---

## 4. Config/확장성

- Detector/Config는 하위 전략(`conservative`, `mean_reversion`)에서 관리
- 본체에서는 신호 조합/가중치/장기추세 반영만 담당
- 필요시 configs/에 추가 파라미터 분리 가능

---

## 5. 활용 포인트

- 보수적 추세 확인과 평균 회귀 신호를 동시에 반영하여 신뢰도 높은 진입/청산
- 하위 strategies 폴더의 전략 구조와 일관성 있게 연동되어 유지보수/확장에 유리
- 신호 발생 근거가 상세하게 기록되어, 디버깅/설명/자동화에 용이
- Factory 의존성 없이 실제 전략 클래스를 직접 참조하므로, 구조가 명확하고 순환참조 위험이 적음

---

## 6. 사용 예시

```python
from domain.strategies.conservative_reversion_hybrid.conservative_reversion_hybrid_strategy import ConservativeReversionHybridStrategy
from domain.signals.strategy.configs.static_strategies import StrategyType, get_strategy_config

config = get_strategy_config(StrategyType.CONSERVATIVE_REVERSION_HYBRID)
strategy = ConservativeReversionHybridStrategy(StrategyType.CONSERVATIVE_REVERSION_HYBRID, config)
strategy.initialize()
# ... 데이터 입력 및 analyze 등 메서드 호출
```

---

## 7. 변경 이력

- 2024-07-09: 기존 Factory 기반 하위 전략 참조 구조에서, 실제 strategies 패키지의 전략 클래스를 직접 import하여 인스턴스화하도록 구조 개선 