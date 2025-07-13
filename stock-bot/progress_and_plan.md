# Stock Bot 전략 시스템 리팩토링 진행상황 및 계획

---

## 1. 프로젝트 목표 및 설계 철학

- **Detector 계층화**: Base > 기본 > 커스텀 구조로 재사용성과 확장성 극대화
- **전략별 패키지화**: 각 전략별로 configs, detectors, 구현체를 독립적으로 관리하여 응집도 향상
- **신호 근거 일관성**: 모든 Detector가 상세 근거(TechnicalIndicatorEvidence)를 일관되게 반환
- **유지보수/확장성**: 새로운 전략/Detector 추가 시 기존 구조를 해치지 않고 확장 가능

---

## 2. 최종 폴더/클래스 구조 설계

```
domain/
  analysis/
    detectors/                    # 공통 기본 Detector들
      base_signal_detector.py
      volume/volume_detector.py
      momentum/rsi_detector.py
      ...
  strategies/                    # 전략별 패키지
    aggressive/
      aggressive_strategy.py
      configs/aggressive_config.py
      detectors/aggressive_volume_detector.py
      detectors/aggressive_sma_detector.py
    balanced/
      balanced_strategy.py
      configs/balanced_config.py
      detectors/balanced_volume_detector.py
      detectors/balanced_sma_detector.py
    conservative/
      conservative_strategy.py
      configs/conservative_config.py
      detectors/conservative_volume_detector.py
      detectors/conservative_sma_detector.py
    ...
```

---

## 3. 단계별 실행계획

### ✅ 1단계: 전략별 패키지 구조 설계 및 생성 (완료)
- domain/strategies/ 하위에 aggressive, balanced, conservative 등 폴더 생성
- 각 폴더 내 configs/, detectors/, 전략 구현체 파일 분리

### ✅ 2단계: Detector 계층 리팩토링 (완료)
- 공통 Detector는 기본 구현 제공 (domain/analysis/detectors/)
- 전략별 커스텀 Detector는 각 전략 패키지의 detectors/에 위치
- 모든 Detector가 TechnicalIndicatorEvidence 등 상세 근거를 일관되게 반환하도록 개선

### ✅ 3단계: Aggressive 전략 커스텀 Detector 및 전략 구현 (완료)
- AggressiveVolumeDetector, AggressiveSMADetector 등 커스텀 Detector 구현
- aggressive_strategy.py에서 커스텀/기본 Detector 조합, 점수 조정, 상세 근거 수집 등 완성
- 마크다운/설명 블록 제거 및 코드 정리 완료

### ⏳ 4단계: Balanced/Conservative 전략 커스텀 Detector 및 전략 구현 (진행 중)
- Balanced: 커스텀 Detector, config, 전략 구현체 구조 설계 및 일부 구현
- Conservative: 커스텀 Detector, config, 전략 구현체 구조 설계 및 일부 구현

### ⏳ 5단계: 테스트 및 통합 검증 (예정)
- 각 전략별 단위/통합 테스트
- 신호 근거, 점수, 전략별 동작 검증

### ⏳ 6단계: 문서화/자동화/최적화 (예정)
- 구조/사용법/확장법 문서화
- 자동화 스크립트, 코드 최적화 등

---

## 4. 각 전략별 진행상황 상세

### Aggressive 전략
- [x] AggressiveVolumeDetector, AggressiveSMADetector 등 커스텀 Detector 구현
- [x] aggressive_strategy.py 완성 (점수 조정, 근거 수집, 쿨다운, 예외처리 등)
- [x] 마크다운/설명 블록 제거, Python 코드만 남도록 정리
- [x] 커밋 완료

### Balanced 전략
- [x] 패키지/구조 설계 및 생성
- [x] 커스텀 Detector 일부 구현 (BalancedVolumeDetector, BalancedSMADetector)
- [x] config, 전략 구현체 일부 구현
- [ ] 전략 본체 및 나머지 Detector 구현 필요

### Conservative 전략
- [x] 패키지/구조 설계 및 생성
- [x] 커스텀 Detector 일부 구현 (ConservativeVolumeDetector, ConservativeSMADetector)
- [x] config, 전략 구현체 일부 구현
- [ ] 전략 본체 및 나머지 Detector 구현 필요

---

## 5. 향후 TODO 및 관리 팁

- [ ] Balanced/Conservative 전략의 나머지 Detector 및 전략 본체 구현
- [ ] 모든 전략에 대해 단위/통합 테스트 작성 및 검증
- [ ] 신호 근거, 점수, 전략별 동작에 대한 리포트/로그 체계화
- [ ] 문서화(README, 구조/확장법, 예시 등) 및 자동화 스크립트 추가
- [ ] 신규 전략/Detector 추가 시, 기존 구조/패턴을 준수하여 일관성 유지

---

**컨텍스트가 길어질 경우, 이 문서만 최신화하여 관리하면 전체 진행상황과 계획을 한눈에 파악할 수 있습니다.** 