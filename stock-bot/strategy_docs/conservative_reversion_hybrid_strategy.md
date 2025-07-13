# Conservative Reversion Hybrid 전략

---

## 1. 전략 개요

- **Conservative Reversion Hybrid**는 보수적 추세 확인(CONSERVATIVE)과 평균 회귀 진입(MEAN_REVERSION)을 결합한 하이브리드 전략입니다.
- 보수적 전략으로 큰 추세를 확인한 뒤, 평균 회귀 신호에 따라 진입/청산합니다.
- 추세 동의 시 보너스, 반대 시 페널티, 장기추세 가중치 등 다양한 필터링/조합 로직이 적용됩니다.

---

## 2. 전략 구조 및 신호 생성 방식

### 1) 조합 구조
- **하위 전략:**
    - CONSERVATIVE (추세 확인)
    - MEAN_REVERSION (평균 회귀 진입)
- **조합 방식:** 하이브리드(직렬 조합)
- **Detector:** 별도 커스텀 Detector 없음 (하위 전략의 Detector를 그대로 사용)

### 2) 신호 생성 로직
- CONSERVATIVE 전략으로 큰 추세(상승/하락)를 확인합니다.
- MEAN_REVERSION 전략으로 평균 회귀 신호(진입/청산 타이밍)를 포착합니다.
- 평균 회귀 신호가 발생했을 때, 보수적 전략이 같은 방향(상승/하락)에 동의하면 보너스 점수(50%)를 부여합니다.
- 반대 방향이면 페널티(점수 0.5배)를 적용합니다.
- 장기추세(일봉 등)가 BULLISH/BEARISH일 경우 추가 가중치(1.2배)를 적용합니다.
- 최종적으로 buy/sell 점수 중 임계값(6.0) 이상인 쪽이 신호로 채택됩니다.

### 3) 기술적 근거(evidence) 수집
- 하위 전략(CONSERVATIVE, MEAN_REVERSION)에서 발생한 모든 신호 근거(TechnicalIndicatorEvidence)를 통합하여 기록합니다.
- 최종 결과에는 두 전략의 근거가 모두 포함되어, 신호의 신뢰도와 설명력을 높입니다.

---

## 3. 활용 포인트
- 추세장과 횡보장 모두에서 신호의 신뢰도와 안정성을 높일 수 있습니다.
- 단일 평균회귀 전략 대비 거짓 신호가 줄어들고, 보수적 진입이 가능합니다.
- 각 전략별 근거가 모두 기록되어 디버깅과 설명에 유리합니다.
- 임계값(6.0)이 낮아 적당한 빈도의 신호를 생성합니다.
- 리스크 관리와 신뢰도 높은 진입 타이밍이 중요한 투자자에게 적합합니다.

---

## 4. 예시 코드 (사용법)

```python
from domain.strategies.conservative_reversion_hybrid import ConservativeReversionHybridStrategy
from domain.analysis.strategy.configs.static_strategies import StrategyType, STRATEGY_CONFIGS

# 전략 인스턴스 생성
config = STRATEGY_CONFIGS[StrategyType.CONSERVATIVE_REVERSION_HYBRID]
strategy = ConservativeReversionHybridStrategy(StrategyType.CONSERVATIVE_REVERSION_HYBRID, config)
strategy.initialize()

# 신호 분석
result = strategy.analyze(df, ticker, market_trend, long_term_trend, extra_indicators)
print(result)
```

---

## 5. 참고 사항
- 하위 전략(CONSERVATIVE, MEAN_REVERSION)은 각각 독립적으로 구현되어 있어야 하며, 내부적으로 자동 생성/초기화됩니다.
- Detector를 직접 구현하지 않고, 하위 전략의 Detector를 그대로 사용합니다.
- 임계값, 가중치 등은 config에서 조정 가능합니다.
- StrategyManager에서 strategy_type="conservative_reversion_hybrid"로 설정 시 자동으로 이 전략이 활성화됩니다.

---

## 6. 버전 및 변경 이력
- 2024-07-09: 독립 패키지화 및 문서 최초 작성 