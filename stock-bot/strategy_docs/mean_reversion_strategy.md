# mean_reversion 전략 문서

---

## 1. 전략 개요

**mean_reversion**은 과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 정적 전략입니다.

- **조합 Detector**: BB(볼린저밴드, mean_reversion), RSI, Stoch
- **config 기반 동적 Detector 조합**: Detector별 가중치/파라미터를 config에서 일관 관리
- **전용 래퍼 클래스 사용**: MeanReversionBBSignalDetector, MeanReversionRSISignalDetector, MeanReversionStochSignalDetector
- **임계값**: 7.0 (표준)
- **포지션 관리**: 최대 4개, 24시간 보유(단기)
- **폴더 구조**: `domain/strategies/mean_reversion/` (구현체, config, detector 완전 독립)

---

## 2. 신호 생성 로직

1. **config 기반 Detector 동적 생성**
   - config.detectors에 정의된 detector_class, weight, 파라미터를 기반으로 Detector 인스턴스 동적 생성
   - Detector 추가/변경 시 config만 수정하면 자동 반영

2. **Orchestrator 조합**
   - SignalDetectionOrchestrator에 각 Detector를 등록하여 신호 탐지

3. **점수/근거 수집 및 가중치 적용**
   - 각 Detector의 점수, 근거(TechnicalIndicatorEvidence) 상세 기록
   - 시장/장기추세에 따라 buy/sell score 가중치 조정

---

## 3. 주요 파라미터 및 설정

- **signal_threshold**: `7.0`
- **detectors**: config에서 관리 (가중치, 파라미터 포함)
- **position_management**: `{ "max_positions": 4, "position_timeout_hours": 24 }`
- **config 위치**: `domain/strategies/mean_reversion/configs/mean_reversion_config.py`

---

## 4. 예시 코드

```python
from domain.strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy
from domain.strategies.mean_reversion.configs.mean_reversion_config import MEAN_REVERSION_CONFIG

strategy = MeanReversionStrategy()
strategy.initialize()

result = strategy.analyze(df, ticker, market_trend, long_term_trend)

if result.has_signal:
    print(f"신호 발생! 점수: {result.total_score}, 근거: {result.signals_detected}")
```

---

## 5. 활용 포인트

- **과매수/과매도 후 평균 회귀 신호 포착**
- **단기/중기 변동성 구간에서 mean reversion 기회 탐지**
- **Detector별 근거가 모두 기록되어 설명력/디버깅에 유리**
- **Detector 추가/변경 시 config만 수정하면 자동 반영**

---

## 6. 폴더/구현 구조

```
domain/strategies/mean_reversion/
  ├── __init__.py
  ├── configs/
  │    ├── __init__.py
  │    └── mean_reversion_config.py
  ├── detectors/
  │    ├── __init__.py
  │    ├── mean_reversion_bb_detector.py
  │    ├── mean_reversion_rsi_detector.py
  │    └── mean_reversion_stoch_detector.py
  └── mean_reversion_strategy.py
```

---

## 7. 참고
- aggressive, balanced 등 다른 전략과 구조/코딩 스타일을 통일
- Detector/가중치/파라미터 관리가 config에 집중되어 유지보수/확장성 우수
- 기존 domain/analysis/strategy/implementations/mean_reversion_strategy.py는 deprecated 