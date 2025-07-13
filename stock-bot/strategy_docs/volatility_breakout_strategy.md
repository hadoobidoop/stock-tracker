# Volatility Breakout 전략 (변동성 돌파)

---

## 1. 전략 개요

- **전략명:** Volatility Breakout (변동성 돌파)
- **폴더 구조:** `domain/strategies/volatility_breakout/`
- **완전 독립 패키지:** Detector, config, 전략 본체가 모두 폴더 내에서 독립적으로 관리됨
- **주요 신호:** 볼린저밴드(BB) breakout, ADX, 거래량 급증 신호를 조합하여 변동성 응축(squeeze) 후 돌파 구간을 포착

---

## 2. 폴더/클래스 구조

```
domain/strategies/volatility_breakout/
  volatility_breakout_strategy.py         # 전략 본체
  configs/
    volatility_breakout_config.py         # Detector 가중치, 파라미터 등 설정
  detectors/
    volatility_breakout_bb_detector.py    # BB breakout Detector 래퍼
    volatility_breakout_adx_detector.py   # ADX Detector 래퍼
    volatility_breakout_volume_detector.py# 거래량 Detector 래퍼
```

---

## 3. 신호 생성 로직

- **BB breakout:** 볼린저밴드 폭이 좁은(squeeze) 상태에서 상단/하단 돌파 이벤트 및 지속 상태를 포착
- **ADX:** ADX(14) > 25일 때 강한 추세 신호(+DI/-DI 비교)
- **Volume:** 거래량 급증(현재 > 20일평균×계수), 3일 연속 증가 등
- **조합:** 각 Detector의 점수에 가중치를 곱해 합산, 임계값(6.0) 이상이면 신호 발생
- **근거:** 각 Detector별로 신호 발생 근거(TechnicalIndicatorEvidence)를 상세 기록

---

## 4. Config 관리

- Detector별 가중치, 파라미터는 `configs/volatility_breakout_config.py`에서 분리 관리
- 예시:
  ```python
  DETECTOR_CONFIGS = [
      {"detector_class": "VolatilityBreakoutBBDetector", "weight": 7.0, "detector_type": "breakout"},
      {"detector_class": "VolatilityBreakoutADXDetector", "weight": 4.0},
      {"detector_class": "VolatilityBreakoutVolumeDetector", "weight": 5.0},
  ]
  ```

---

## 5. 활용 포인트

- 변동성 응축 후 돌파 구간을 빠르게 포착하여 단기 매매에 활용
- 신호 발생 근거가 상세하게 기록되어, 디버깅/설명/자동화에 용이
- Detector/Config가 완전히 분리되어 유지보수/확장에 매우 유리

---

## 6. 사용 예시

```python
from domain.strategies.volatility_breakout.volatility_breakout_strategy import VolatilityBreakoutStrategy
from domain.strategies.volatility_breakout.configs.volatility_breakout_config import DETECTOR_CONFIGS

strategy = VolatilityBreakoutStrategy(config=DETECTOR_CONFIGS)
# ... 데이터 입력 및 analyze 등 메서드 호출
```

---

## 7. 변경 이력

- 2024-07-09: 기존 domain/analysis/strategy/implementations/volatility_breakout_strategy.py 및 Detector를 완전 독립 구조로 이전
- 2024-07-09: config 분리, 래퍼 Detector 도입, Factory/Manager 경로 수정, 문서화 