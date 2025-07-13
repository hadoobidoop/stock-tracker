# MultiTimeframe(다중 시간대) 전략 문서

---

## 1. 전략 개요 및 설계 의도

- **MultiTimeframe(다중 시간대) 전략**은 장기(일봉)와 단기(시간봉) 신호를 동시에 확인하여 신뢰도 높은 진입/청산 신호를 포착하는 전략입니다.
- MACD, Stoch, RSI 등 주요 기술적 지표를 활용하며, **복합 컨펌 로직은 MultiTimeframeCompositeDetector**에서 일괄 처리합니다.
- 모든 전략 파라미터(config)는 configs/multi_timeframe_config.py에서 관리하며, Detector 구조와 신호 컨펌 로직도 쉽게 확장할 수 있습니다.

---

## 2. 폴더/구조

```
domain/strategies/multi_timeframe/
  multi_timeframe_strategy.py                # 전략 본체 (완전 독립)
  configs/
    multi_timeframe_config.py                # 전략 파라미터(상수 dict)
  detectors/
    (래퍼 Detector는 미사용, 필요시 추가)
domain/analysis/detectors/composite/
  multi_timeframe_composite_detector.py      # 다중 시간대 복합 Detector (핵심)
```

---

## 3. 주요 파라미터(config)

- **signal_threshold:** 9.0 (신호 발생 임계값)
- **risk_per_trade:** 0.02 (거래당 리스크 비율)
- **detector_weights:**
    - composite: 7.0 (복합 Detector 가중치)
- **market_filters:** {"multi_timeframe_confirmation": True}
- **position_management:** {"max_positions": 3, "position_timeout_hours": 504}
- **config 위치:** `domain/strategies/multi_timeframe/configs/multi_timeframe_config.py`

---

## 4. Detector 구조 및 신호 생성 로직

- **MultiTimeframeCompositeDetector** 단일 조합만 사용합니다.
    - 일봉/시간봉 데이터 동시 분석, 추세 컨센서스, 신호 강도 계산 등 복합 컨펌 로직 내장
    - 기존 MACD, Stoch, RSI 래퍼 Detector는 미사용(필요시 확장 가능)
- 전략 본체에서 복합 Detector만을 orchestrator에 등록하여 신호를 생성합니다.

---

## 5. 신호 생성 로직

1. **복합 Detector 단일 조합**
    - MultiTimeframeCompositeDetector(weight=config['detector_weights']['composite'])
    - 일봉/시간봉 데이터, 추세 컨센서스, 신호 강도 등 모든 컨펌 로직을 내부에서 처리
2. **Orchestrator 조합**
    - SignalDetectionOrchestrator에 복합 Detector만 등록
3. **점수/근거 수집 및 가중치 적용**
    - 복합 Detector의 점수, 근거(TechnicalIndicatorEvidence) 상세 기록
    - 시장/장기추세에 따라 buy/sell score 가중치 조정

---

## 6. 사용 예시

```python
from domain.strategies.multi_timeframe.multi_timeframe_strategy import MultiTimeframeStrategy
strategy = MultiTimeframeStrategy()
strategy.initialize()
result = strategy.analyze(df, ticker, market_trend, long_term_trend, daily_extra_indicators)
```

---

## 7. 확장 포인트

- 복합 Detector 내부 로직(추세 컨센서스, 신호 강도 등) 커스터마이즈 가능
- 필요시 detectors/ 하위에 개별 래퍼 Detector 추가 및 config에서 동적 조합 가능
- config 파라미터만 수정해 전략 튜닝 가능
- 전략 구조가 완전히 독립적이므로, 유지보수/확장/테스트가 매우 용이함

---

## 8. 참고/관리 팁

- 모든 전략 파라미터, Detector 구조, 신호 생성 로직은 이 문서와 config 파일만 최신화하면 전체 구조를 한눈에 파악할 수 있습니다.
- 커스텀 Detector, 신호 컨펌 로직, 포지션 관리 등 다양한 실험/확장에 적합한 구조입니다. 