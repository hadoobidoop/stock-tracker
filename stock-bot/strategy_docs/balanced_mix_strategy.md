# balanced_mix 전략 조합 (Balanced Mix)

---

## 1. 전략 개요

- **balanced_mix**는 추세추종(Trend Following)과 평균회귀(Mean Reversion) 전략을 50:50 가중치로 조합하여 다양한 시장 상황에 균형 있게 대응하는 정적 전략 조합입니다.
- 각 하위 전략의 신호(점수, 근거 등)를 가중 평균하여 최종 신호를 산출합니다.
- 임계값 조정(threshold_adjustment=1.0, 기본 임계값 8.0)으로 신호 발생 기준을 설정합니다.
- 신호 발생 시 모든 하위 전략의 근거(TechnicalIndicatorEvidence)를 통합하여 제공합니다.

---

## 2. 조합 구조 및 신호 생성 방식

### 1) 조합 구성
- **조합 방식:** WEIGHTED (가중치 기반)
- **구성 전략:**
    - TREND_FOLLOWING (추세추종) : 50%
    - MEAN_REVERSION (평균회귀)   : 50%
- **임계값 조정:** 1.0 (기본 임계값 8.0)

### 2) 신호 생성 로직
- 각 하위 전략을 독립적으로 실행하여 개별 결과(점수, 근거 등)를 수집합니다.
- 가중치 기반 조합: 각 전략의 점수에 가중치(0.5, 0.5)를 곱해 가중 평균을 계산합니다.
- 최종 점수 = (TREND_FOLLOWING 점수 × 0.5 + MEAN_REVERSION 점수 × 0.5)
- 조정된 임계값(8.0) 이상이면 신호 발생, 매수/매도 중 점수가 높은 쪽이 채택됩니다.

### 3) 기술적 근거(evidence) 수집
- 각 하위 전략별로 신호 발생 근거(TechnicalIndicatorEvidence)를 개별 수집/기록합니다.
- 최종 결과에는 모든 하위 전략의 근거가 포함되어, 신호의 설명력과 신뢰도를 높입니다.
- 전략명: "Mix(추세추종 전략(0.5)+평균회귀 전략(0.5))" 형태로 표시됩니다.

---

## 3. 활용 포인트
- 추세장과 횡보장 모두에 균형 있게 대응할 수 있습니다.
- 단일 전략 대비 신호의 일관성과 안정성이 높아집니다.
- 각 전략별 근거가 모두 기록되어 디버깅과 설명에 유리합니다.
- 임계값이 표준(8.0)으로 적당한 빈도의 신호를 생성합니다.
- 다양한 시장 상황에서 리스크 분산 효과를 기대할 수 있습니다.

---

## 4. 예시 코드 (사용법)

```python
from domain.strategies.balanced_mix import BalancedMixStrategy
from domain.strategies.trend_following.trend_following_strategy import TrendFollowingStrategy
from domain.strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy
from domain.analysis.strategy.configs.static_strategies import StrategyType

# 하위 전략 인스턴스 생성
trend_following = TrendFollowingStrategy(...)
mean_reversion = MeanReversionStrategy(...)

# balanced_mix 조합 전략 생성 및 하위 전략 등록
mix_strategy = BalancedMixStrategy()
mix_strategy.register_sub_strategies({
    StrategyType.TREND_FOLLOWING: trend_following,
    StrategyType.MEAN_REVERSION: mean_reversion
})

# 신호 분석
result = mix_strategy.analyze(df, ticker, market_trend, long_term_trend)
print(result)
```

---

## 5. 참고 사항
- 하위 전략(Trend Following, Mean Reversion)은 각각 독립적으로 구현되어 있어야 하며, `register_sub_strategies`로 인스턴스를 등록해야 합니다.
- 임계값, 가중치 등은 config에서 조정 가능합니다.
- StrategyManager에서 mix_name="balanced_mix"로 설정 시 자동으로 이 조합이 활성화됩니다.

---

## 6. 버전 및 변경 이력
- 2024-07-09: 독립 패키지화 및 문서 최초 작성 