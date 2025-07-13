# aggressive_mix 전략 조합 (Aggressive Mix Strategy)

> **모멘텀, 스캘핑, 변동성 돌파 전략을 가중치 기반으로 조합하여 빠른 신호와 기회를 포착하는 초공격적 조합 전략**

---

## 1. 전략 개요

- **목적:** 단일 전략의 한계를 극복하고, 초단기/모멘텀/변동성 신호를 빠르게 포착
- **핵심:** MOMENTUM(0.4), SCALPING(0.3), VOLATILITY_BREAKOUT(0.3) 전략을 가중 평균으로 조합
- **적합 시장:** 변동성 크고, 단기 기회가 많은 시장, 빠른 매매 선호자

---

## 2. 전략 구조 및 조합 방식

- **구성 전략 및 가중치**
    - MOMENTUM: 40%
    - SCALPING: 30%
    - VOLATILITY_BREAKOUT: 30%
- **조합 방식:** 각 전략의 analyze 결과(점수, 근거 등)를 가중 평균하여 최종 신호 산출
- **임계값 조정:** threshold_adjustment=0.8 (기본 임계값 8.0 → 6.4로 낮춤)
- **최종 신호:** 매수/매도 중 점수가 높은 쪽이 채택, 신호 발생 근거는 모든 하위 전략의 evidence를 통합

---

## 3. 주요 파라미터 (config)

- `strategies`: 조합에 포함된 전략 및 가중치 (MOMENTUM, SCALPING, VOLATILITY_BREAKOUT)
- `mode`: 조합 방식 (WEIGHTED)
- `threshold_adjustment`: 임계값 조정 계수 (0.8)
- `name`, `description`: 조합 이름/설명

---

## 4. 신호 생성 로직

1. **하위 전략별 analyze 실행:**
    - 각 하위 전략의 analyze 메서드 호출, 결과(점수, 근거 등) 수집
2. **가중치 합산:**
    - 각 전략의 점수 × 가중치 → 합산하여 최종 점수 계산
3. **임계값 조정:**
    - 최종 점수가 (8.0 × 0.8 = 6.4) 이상이면 신호 발생
4. **신호 반환:**
    - 매수/매도 중 점수가 높은 쪽이 채택, 모든 하위 전략의 근거(evidence) 통합

---

## 5. 활용 포인트 및 특징

- **초공격적/초단기:** 매우 빠른 신호 생성, 단기 기회 적극 포착
- **구성 전략별 근거 통합:** 신호 발생 시 모든 하위 전략의 evidence가 기록되어 설명력/디버깅에 유리
- **낮은 임계값:** 신호 빈도가 높으나, 거짓 신호 위험도 증가 (리스크 관리 필수)
- **유연한 확장:** 하위 전략/가중치/임계값 등 config에서 손쉽게 변경 가능

---

## 6. 사용 예시 (코드)

```python
from domain.strategies.aggressive_mix import AggressiveMixStrategy, AGGRESSIVE_MIX_CONFIG
from domain.strategies.momentum.momentum_strategy import MomentumStrategy
from domain.strategies.scalping.scalping_strategy import ScalpingStrategy
from domain.strategies.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
from domain.analysis.strategy.configs.static_strategies import StrategyType

# 하위 전략 인스턴스 생성 및 등록
momentum = MomentumStrategy(...)
scalping = ScalpingStrategy(...)
vol_breakout = VolatilityBreakoutStrategy(...)

mix_strategy = AggressiveMixStrategy()
mix_strategy.register_sub_strategies({
    StrategyType.MOMENTUM: momentum,
    StrategyType.SCALPING: scalping,
    StrategyType.VOLATILITY_BREAKOUT: vol_breakout
})

result = mix_strategy.analyze(df, ticker, market_trend, long_term_trend)
if result.has_signal:
    print(f"신호 발생! 점수: {result.total_score}, 근거: {result.signals_detected}")
```

---

## 7. 확장/커스터마이징 방법

- 하위 전략/가중치/임계값 등 config에서 손쉽게 변경 가능
- 하위 전략 자체를 커스텀(상속/오버라이드)하여 민감도, 신호 산출 방식 등 세밀 조정 가능
- 신호 근거 통합, confidence 계산 방식 등도 필요에 따라 확장 가능

---

## 8. 참고/유의사항

- 신호 빈도가 매우 높으므로, 실전 적용 전 충분한 백테스트/리스크 관리 필수
- 하위 전략이 모두 독립적으로 동작해야 하며, analyze 메서드 시그니처가 일치해야 함
- 전략 구조/코드는 domain/strategies/aggressive_mix/ 이하에서 완전히 독립적으로 관리됨 