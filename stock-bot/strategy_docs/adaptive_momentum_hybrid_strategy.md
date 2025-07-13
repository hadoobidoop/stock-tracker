# Adaptive Momentum Hybrid 전략 (적응형 모멘텀 하이브리드)

---

## 1. 전략 개요

- **전략명:** Adaptive Momentum Hybrid (적응형 모멘텀 하이브리드)
- **폴더 구조:** `domain/strategies/adaptive_momentum_hybrid/`
- **완전 독립 패키지:** 전략 본체가 폴더 내에서 독립적으로 관리됨
- **하위 전략 연동:** 하위 strategies 폴더(`trend_following/`, `momentum/`)의 정적 전략을 직접 import하여 인스턴스화
- **주요 신호:** 추세(TREND_FOLLOWING)와 모멘텀(MOMENTUM) 전략의 점수를 가중평균(50:50)하여 최종 신호 산출

---

## 2. 폴더/클래스 구조

```
domain/strategies/adaptive_momentum_hybrid/
  adaptive_momentum_hybrid_strategy.py      # 전략 본체
  configs/
    # (필요시 Detector/Config 분리)
  detectors/
    # (필요시 커스텀 Detector 래퍼)

# 하위 전략(연동)
domain/strategies/trend_following/
  trend_following_strategy.py
  ...
domain/strategies/momentum/
  momentum_strategy.py
  ...
```

---

## 3. 신호 생성 로직

- **하위 전략 연동:**
  - `trend_following/`와 `momentum/` 폴더의 전략을 직접 import하여 인스턴스화
  - 각 전략의 `analyze()` 결과에서 buy/sell 점수를 50:50 가중평균
- **장기추세 가중치:**
  - long_term_trend가 BULLISH면 buy_score 1.2배, BEARISH면 sell_score 1.2배
- **최종 신호:**
  - buy/sell 점수 중 높은 쪽이 임계값 이상이면 신호 발생
  - 두 전략의 신호 근거(signals_detected)도 모두 합산

---

## 4. Config/확장성

- Detector/Config는 하위 전략(`trend_following`, `momentum`)에서 관리
- 본체에서는 신호 조합/가중치/장기추세 반영만 담당
- 필요시 configs/에 추가 파라미터 분리 가능

---

## 5. 활용 포인트

- 추세와 모멘텀 신호를 동시에 반영하여 시장 변화에 유연하게 대응
- 하위 strategies 폴더의 전략 구조와 일관성 있게 연동되어 유지보수/확장에 유리
- 신호 발생 근거가 상세하게 기록되어, 디버깅/설명/자동화에 용이
- Factory 의존성 없이 실제 전략 클래스를 직접 참조하므로, 구조가 명확하고 순환참조 위험이 적음

---

## 6. 사용 예시

```python
from domain.strategies.adaptive_momentum_hybrid.adaptive_momentum_hybrid_strategy import AdaptiveMomentumStrategy
from domain.analysis.strategy.configs.static_strategies import StrategyType, get_strategy_config

config = get_strategy_config(StrategyType.ADAPTIVE_MOMENTUM)
strategy = AdaptiveMomentumStrategy(StrategyType.ADAPTIVE_MOMENTUM, config)
strategy.initialize()
# ... 데이터 입력 및 analyze 등 메서드 호출
```

---

## 7. 변경 이력

- 2024-07-09: 기존 domain/analysis/strategy/implementations/adaptive_momentum_hybrid_strategy.py를 완전 독립 구조로 이전
- 2024-07-09: Factory/Manager import 경로 수정, 문서화
- 2024-07-09: 하위 전략을 Factory가 아닌 실제 strategies 패키지의 전략 클래스를 직접 import하여 인스턴스화하도록 구조 개선 