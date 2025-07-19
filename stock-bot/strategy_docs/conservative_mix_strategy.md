# conservative_mix 전략 조합 문서

---

## 1. 전략 개요

**conservative_mix**는 보수적, 고신뢰도, 스윙 전략을 조합하여 매우 안정적이고 신뢰도 높은 신호만을 생성하는 정적 전략 조합입니다.

- **조합 방식**: 투표 기반(VOTING, 과반수 동의)
- **구성 전략**: CONSERVATIVE, SWING (각 1.0, 동등 가중치)
- **임계값 조정**: 1.2 (기본 임계값 8.0 → 9.6)
- **폴더 구조**: `domain/strategies/conservative_mix/` (구현체, config 완전 독립)

---

## 2. 신호 생성 로직

1. **하위 전략 실행**
   - CONSERVATIVE, SWING 전략을 각각 독립적으로 실행하여 결과(점수, 근거 등)를 수집합니다.

2. **투표 기반 조합**
   - 각 전략의 점수가 (임계값 9.6 이상)일 때만 신호로 인정
   - 3개 전략 중 2개 이상이 같은 방향(매수/매도) 신호를 낼 때만 최종 신호로 채택
   - 최종 점수는 신호를 낸 전략 중 가장 높은 점수를 사용
   - 신뢰도는 신호를 낸 전략 수 / 전체 전략 수 (예: 2/3 = 0.67)

3. **기술적 근거(evidence) 수집**
   - 신호를 낸 전략들의 근거(TechnicalIndicatorEvidence)만 최종 결과에 포함
   - 전략명: `Voting(2/3)` 형태로 표시되어 몇 개 전략이 동의했는지 명확히 보여줌

---

## 3. 주요 파라미터 및 설정

- **mode**: `StrategyMixMode.VOTING`
- **strategies**: `{StrategyType.CONSERVATIVE: 1.0, StrategyType.SWING: 1.0}`
- **threshold_adjustment**: `1.2` (임계값 8.0 × 1.2 = 9.6)
- **config 위치**: `domain/strategies/conservative_mix/configs/conservative_mix_config.py`

---

## 4. 예시 코드

```python
from domain.strategies.conservative_mix.conservative_mix_strategy import ConservativeMixStrategy
from domain.strategies.conservative_mix.configs.conservative_mix_config import CONSERVATIVE_MIX_CONFIG
from domain.signals.strategy.configs.static_strategies import StrategyType

# 하위 전략 인스턴스 준비 (예시)
conservative = ...  # ConservativeStrategy 인스턴스
swing = ...        # SwingStrategy 인스턴스

mix_strategy = ConservativeMixStrategy()
mix_strategy.register_sub_strategies({
    StrategyType.CONSERVATIVE: conservative,
    StrategyType.SWING: swing
})

result = mix_strategy.analyze(df, ticker, market_trend, long_term_trend)

if result.has_signal:
    print(f"신호 발생! 점수: {result.total_score}, 근거: {result.signals_detected}")
```

---

## 5. 활용 포인트

- **매우 보수적이고 신뢰도 높은 신호만 생성**
- **거짓 신호(false signal) 최소화, 안정적 거래**
- **각 전략별 근거가 모두 기록되어 설명력/디버깅에 유리**
- **시장 변동성이 크거나, 확실한 기회만 포착하려는 투자자에게 적합**

---

## 6. 폴더/구현 구조

```
domain/strategies/conservative_mix/
  ├── __init__.py
  ├── configs/
  │    ├── __init__.py
  │    └── conservative_mix_config.py
  └── conservative_mix_strategy.py
```

---

## 7. 참고
- aggressive_mix, balanced_mix 등 다른 조합 전략과 구조/코딩 스타일을 통일
- strategy_manager에서 직접 CONSERVATIVE_MIX_CONFIG를 import하여 사용
- 기존 strategy_mixes.py 정의는 제거됨(이 파일 참고) 