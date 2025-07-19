# SCALPING 전략 (Scalping Strategy)

> **초단기(4시간 이내) 매매, 빠른 진입/청산, 변동성(VIX) 기반 점수 조정에 특화된 전략**

---

## 1. 전략 개요

- **목적:** 초단기(4시간 이내) 매매에서 빠른 진입/청산 기회를 포착
- **핵심:** RSI, Stoch, Volume, MACD 등 민감한 신호 조합 + VIX(변동성지수) 기반 점수 조정
- **적합 시장:** 변동성 크고, 단기 기회가 많은 시장

---

## 2. 전략 구조 및 Detector 조합

- **주요 Detector 및 가중치**
    - RSI: 4.0
    - Stoch: 4.0
    - Volume: 5.0 (거래량 신호에 가장 민감)
    - MACD: 3.0
- **조합 방식:** 모든 Detector의 신호를 가중치 합산하여 점수 산출
- **VIX 기반 점수 조정:**
    - VIX > 25: 점수 × 1.2 (고변동성 시장에서 신호 강화)
    - VIX < 15: 점수 × 0.8 (저변동성 시장에서 신호 약화)
    - VIX 데이터 없을 시 조정 없음

---

## 3. 주요 파라미터 (config)

- `signal_threshold`: 신호 발생 기준점 (기본 4.0)
- `max_positions`: 최대 동시 포지션 수 (기본 10)
- `position_hold_hours`: 포지션 최대 보유 시간 (기본 4시간)
- `risk_per_trade`: 트레이드당 리스크 비율 (기본 0.01)
- `vix_high_multiplier`: VIX 25 초과 시 점수 배수 (1.2)
- `vix_low_multiplier`: VIX 15 미만 시 점수 배수 (0.8)
- `detector_weights`: 각 Detector별 가중치 (RSI, Stoch, Volume, MACD)

---

## 4. 신호 생성 로직

1. **Detector별 신호 산출:**
    - 각 Detector가 입력 데이터에서 신호(점수, 근거 등) 산출
2. **가중치 합산:**
    - Detector별 점수 × 가중치 → 합산하여 최종 점수 계산
3. **VIX 기반 점수 조정:**
    - VIX 값에 따라 최종 점수에 배수 적용
4. **임계값 비교:**
    - 최종 점수가 `signal_threshold` 이상이면 신호 발생
5. **신호 반환:**
    - 매수/매도 점수, 신호 근거, 신뢰도 등 포함한 `StrategyResult` 반환

---

## 5. 활용 포인트 및 특징

- **초단기 매매:** 4시간 이내 빠른 진입/청산, 높은 빈도의 신호
- **거래량 신호 중시:** Volume Detector 가중치가 가장 높음
- **변동성 필터:** VIX에 따라 신호 민감도 자동 조정
- **리스크 관리:** 포지션 수, 보유 시간, 트레이드당 리스크 등 config로 세밀하게 제어
- **설명력:** 신호 발생 근거(Detector별 상세 evidence) 자동 기록

---

## 6. 사용 예시 (코드)

```python
from domain.strategies.scalping.scalping_strategy import ScalpingStrategy
from domain.strategies.scalping.configs.scalping_config import ScalpingStrategyConfig
from domain.signals.strategy.configs.static_strategies import StrategyType

config = ScalpingStrategyConfig()
strategy = ScalpingStrategy(StrategyType.SCALPING, config)
strategy.initialize()
result = strategy.analyze(df, ticker, market_trend, long_term_trend)

if result.has_signal:
    print(f"신호 발생! 점수: {result.total_score}, 근거: {result.signals_detected}")
```

---

## 7. 확장/커스터마이징 방법

- Detector별 가중치, 신호 기준, VIX 조정 배수 등 config에서 손쉽게 변경 가능
- Detector 자체를 커스텀(상속/오버라이드)하여 민감도, 신호 산출 방식 등 세밀 조정 가능
- 포지션 관리, 리스크 관리 로직도 config에서 일관성 있게 확장

---

## 8. 참고/유의사항

- 신호 빈도가 높으므로, 백테스트/실전 적용 전 리스크 관리 필수
- VIX 데이터가 없을 경우 점수 조정이 생략됨 (로깅으로 확인 가능)
- 전략 구조/코드는 domain/strategies/scalping/ 이하에서 완전히 독립적으로 관리됨 