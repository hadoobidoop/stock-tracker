# Swing(스윙) 전략 문서

---

## 1. 전략 개요 및 설계 의도

- **Swing(스윙) 전략**은 중기 추세 변곡점(전환/반전) 구간에서 진입/청산 신호를 포착하는 전략입니다.
- SMA, MACD, RSI, ADX 등 대표적 추세/모멘텀 지표를 조합하여 신호의 신뢰도와 설명력을 높입니다.
- Detector별 가중치, 임계값, 포지션 관리 등은 완전히 독립된 config(dict)로 관리되어 유지보수/확장성이 뛰어납니다.
- 모든 Detector는 `domain/strategies/swing/detectors/` 하위의 래퍼 클래스를 통해 독립적으로 관리됩니다.

---

## 2. 폴더/구조

```
domain/strategies/swing/
  swing_strategy.py                # 전략 본체 (완전 독립)
  configs/
    swing_config.py                # 전략 파라미터(상수 dict)
  detectors/
    swing_sma_detector.py          # SMA Detector 래퍼
    swing_macd_detector.py         # MACD Detector 래퍼
    swing_rsi_detector.py          # RSI Detector 래퍼
    swing_adx_detector.py          # ADX Detector 래퍼
```

---

## 3. 주요 파라미터(config)

- **임계값(signal_threshold):** 7.0
- **리스크(risk_per_trade):** 0.025
- **포지션 관리:** max_positions=3, position_timeout_hours=336(14일)
- **detector_weights:**
    - SMA: 5.0
    - MACD: 6.0
    - RSI: 4.0
    - ADX: 4.0
- **market_filters:** trend_alignment=False
- **구현체:** `domain.strategies.swing.swing_strategy.SwingStrategy`

---

## 4. 신호 생성 로직

1. **Detector 조합**
    - swing/detectors 하위의 커스텀 래퍼 Detector 4종(SMA, MACD, RSI, ADX) 사용
    - 각 Detector의 가중치는 config['detector_weights']에서 관리
2. **신호 분석**
    - SignalDetectionOrchestrator로 각 Detector의 신호/점수/근거를 종합
    - 시장 중립(NEUTRAL) 시 점수 1.15배(스윙 특화)
    - 장기추세(BULLISH/BEARISH) 가중치 buy/sell에 적용
    - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
3. **쿨다운/예외처리**
    - 중복 신호 방지, 예외 발생 시 안전하게 실패 반환

---

## 5. 예시 코드

```python
from domain.strategies.swing.swing_strategy import SwingStrategy
from domain.signals.strategy.configs.static_strategies import StrategyType

# 전략 인스턴스 생성
strategy = SwingStrategy(StrategyType.SWING)
strategy.initialize()

# 신호 분석
result = strategy.analyze(df, ticker, market_trend, long_term_trend)

print(result.has_signal, result.total_score, result.buy_score, result.sell_score)
```

---

## 6. 활용 포인트 및 유지보수 팁

- 중기(수일~수주) 추세 전환/반전 구간에서 진입/청산 신호 포착에 적합
- Detector별 상세 근거 기록, 전략별 파라미터 튜닝 용이
- config(dict) 기반 구조로 유지보수/확장/테스트가 독립적으로 가능
- Detector 추가/변경 시 swing/detectors/ 하위에 래퍼만 추가하면 됨
- 전략별 주석/문서화가 상세하게 되어 있어 신규 개발자도 쉽게 이해 가능

---

## 7. 변경 이력

- 2024-07-** (최신) 완전 독립 구조로 리팩토링, config 상수화, 커스텀 Detector 래퍼 구조 적용, 상세 주석/문서화 