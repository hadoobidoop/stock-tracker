# Stock Bot 전략 시스템 리팩토링 진행상황 및 계획

---

## 1. 프로젝트 목표 및 설계 철학

- **Detector 계층화**: Base > 기본 > 커스텀 구조로 재사용성과 확장성 극대화
- **전략별 패키지화 및 독립성**: 앞으로 모든 전략(정적/동적/조합 포함)은 해당 전략별 폴더(domain/strategies/...)에 구현체/Detector/config를 완전히 독립적으로 관리하는 구조로 일원화할 계획입니다. 이로써 각 전략은 폴더 단위로 완전히 분리되어, 유지보수/확장/테스트가 독자적으로 가능해집니다.
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
  strategies/                    # 전략별 패키지 (각 전략별로 완전히 독립적 관리)
    aggressive/
      aggressive_strategy.py      # aggressive 전략 구현체 (폴더 내 독립 관리)
      configs/aggressive_config.py
      detectors/aggressive_volume_detector.py
      detectors/aggressive_sma_detector.py
    balanced/
      balanced_strategy.py        # balanced 전략 구현체 (폴더 내 독립 관리)
      configs/balanced_config.py
      detectors/balanced_volume_detector.py
      detectors/balanced_sma_detector.py
    conservative/
      conservative_strategy.py    # conservative 전략 구현체 (폴더 내 독립 관리)
      configs/conservative_config.py
      detectors/conservative_volume_detector.py
      detectors/conservative_sma_detector.py
    ...
```

> 현재 aggressive, balanced, conservative 전략은 이미 독립 구조로 완전히 이전 완료(구현체, Detector, config 모두 폴더 내에 위치).
> 기타 전략(예: momentum, mean_reversion, swing 등)은 추후 동일한 방식으로 이전 예정.
### 전체 전략 리스트 및 독립화/리팩토링 현황

| 전략명                | 폴더 독립화/리팩토링 현황 |
|----------------------|--------------------------|
| Aggressive           | 완료                     |
| Balanced             | 완료                     |
| Conservative         | 완료 (조합 포함)         |
| Momentum             | 완료                     |
| Scalping             | 완료                     |
| aggressive_mix       | 완료 (조합)              |
| Mean Reversion       | 완료                     |
| Swing                | 예정                     |
| Trend Following      | 완료                     |
| Trend Pullback       | 완료                     |
| Contrarian           | 예정                     |
| Volatility Breakout  | 완료                     |
| Macro Driven         | 예정                     |
| Multi Timeframe      | 예정                     |
| Quality Trend        | 예정                     |
| Stable Value Hybrid  | 예정                     |
| Market Regime Hybrid | 완료                     |
| Adaptive Momentum Hybrid | 완료                 |
| Conservative Reversion Hybrid | 완료           |
| balanced_mix         | 완료 (조합)              |
| conservative_mix     | 완료 (조합)              |
| Dynamic Strategy/Manager | 예정 (동적)         |

> Aggressive, Balanced, Conservative, Momentum 전략 모두 독립 구조로 완전히 이전 완료. 나머지 전략/조합/동적 전략은 동일 방식으로 이전 예정.

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

### Aggressive/ Balanced/ Conservative/ Momentum/Scalping/aggressive_mix/conservative_mix/mean_reversion/balanced_mix/conservative_reversion_hybrid 전략
- 각 전략별 구현체(.py), Detector, config, (조합 전략은 실행체/config)는 해당 전략 폴더 내에서 완전히 독자적으로 관리됨 (폴더 단위 독립성)
- aggressive, balanced, conservative, momentum, scalping, aggressive_mix, conservative_mix, mean_reversion, balanced_mix, conservative_reversion_hybrid 전략은 독립 구조로 완전히 이전 완료 및 문서화/주석 리팩토링까지 완료
- swing 등 기타 전략/조합/동적 전략은 추후 동일한 방식으로 이전 예정

### Aggressive 전략
- [x] AggressiveVolumeDetector, AggressiveSMADetector 등 커스텀 Detector 구현
- [x] aggressive_strategy.py 완성 (점수 조정, 근거 수집, 쿨다운, 예외처리 등)
- [x] 마크다운/설명 블록 제거, Python 코드만 남도록 정리
- [x] 커밋 완료

### Balanced 전략
- [x] 패키지/구조 설계 및 생성
- [x] 커스텀 Detector 일부 구현 (BalancedVolumeDetector, BalancedSMADetector)
- [x] config, 전략 구현체 일부 구현
- [x] 전략 본체 및 나머지 Detector 구현 완료
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료

### Conservative 전략
- [x] 패키지/구조 설계 및 생성
- [x] 커스텀 Detector 구현 (ConservativeVolumeDetector, ConservativeSMADetector)
- [x] config, 전략 본체 구현 및 이전
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] 전략/디텍터/설정 주석 리팩토링 및 가독성 개선
- [x] 커밋 완료

### Momentum 전략
- [x] Momentum 전략 폴더/구조 설계 및 생성
- [x] 커스텀 Detector, config, 전략 구현체 구현 및 완성
- [x] 전략 본체 및 Detector 구현 완료
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료

### Scalping 전략
- [x] 패키지/구조 설계 및 생성
- [x] Detector, config, 전략 구현체 완전 분리 및 경로/구조 일관화
- [x] 전략 본체 및 Detector 구현 완료
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료

### aggressive_mix 전략 조합
- [x] 패키지/구조 설계 및 생성
- [x] config, 실행체(조합 전략) 완전 분리 및 경로/구조 일관화
- [x] 기존 strategy_mixes.py에서 정의 제거 및 안내
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료

### Conservative_mix 전략
- [x] conservative_mix 폴더/구조 설계 및 생성
- [x] config, 실행체(조합 전략) 완전 분리 및 경로/구조 일관화
- [x] 기존 strategy_mixes.py에서 정의 제거 및 안내
- [x] StrategyManager에서 import 경로 분기 처리 및 일관화
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료

### Mean Reversion 전략
- [x] mean_reversion 폴더/구조 설계 및 생성
- [x] config, detector 래퍼, 실행체 완전 분리 및 경로/구조 일관화
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] Detector 가중치/파라미터 config화 및 동적 생성 구조 반영
- [x] 주석/문서화/튜닝 가이드/strategy_docs 최신화 및 커밋 완료

### balanced_mix 전략 조합
- [x] balanced_mix 폴더/구조 설계 및 생성
- [x] config, 실행체(조합 전략) 완전 분리 및 경로/구조 일관화
- [x] 기존 strategy_mixes.py에서 정의 제거 및 안내
- [x] StrategyManager에서 import 경로 분기 처리 및 일관화
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료
- [x] strategy_docs/balanced_mix_strategy.md 문서화 완료

### Conservative Reversion Hybrid 전략
- [x] conservative_reversion_hybrid 폴더/구조 설계 및 생성
- [x] 전략 구현체 완전 분리 및 경로/구조 일관화
- [x] StrategyFactory, static_strategies.py 등 import/implementation_class 경로 일괄 수정
- [x] 기존 레거시 파일 삭제
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료
- [x] strategy_docs/conservative_reversion_hybrid_strategy.md 문서화 완료

### Volatility Breakout 전략
- [x] 패키지/구조 설계 및 생성
- [x] 커스텀 Detector, config, 전략 구현체 구조 설계 및 일부 구현
- [x] 커스텀 Detector 구현 (VolatilityBreakoutVolumeDetector, VolatilityBreakoutSMADetector)
- [x] config, 전략 본체 구현 및 이전
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] 전략/디텍터/설정 주석 리팩토링 및 가독성 개선
- [x] 커밋 완료
- [x] 문서화/주석 리팩토링 완료

### Adaptive Momentum Hybrid 전략
- [x] 폴더/구조 설계 및 생성
- [x] 커스텀 Detector, config, 전략 구현체 구현 및 완성
- [x] 전략 본체 및 Detector 구현 완료
- [x] 주석/문서화/튜닝 가이드 보강 및 커밋 완료
- [x] 하위 strategies 폴더 연동 구조 반영
- [x] 문서화/주석 리팩토링 완료

### Trend Pullback 전략
- [x] trend_pullback 폴더/구조 설계 및 생성
- [x] 커스텀 Detector(TrendPullbackSMADetector, TrendPullbackADXDetector, TrendPullbackRSIDetector) 구현 및 분리
- [x] config(trend_pullback_config.py) 분리 및 가중치/파라미터 관리
- [x] 전략 본체(trend_pullback_strategy.py) 완전 분리 및 경로/구조 일관화
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] 상세 로그(info/debug) 추가 및 백테스트/실시간 분석 활용성 강화
- [x] strategy_docs/trend_pullback_strategy.md 문서화 완료
- [x] 커밋 완료

### Trend Following 전략
- [x] trend_following 폴더/구조 설계 및 생성
- [x] 커스텀 Detector(TrendFollowingSMADetector, TrendFollowingMACDDetector, TrendFollowingADXDetector, TrendFollowingVolumeDetector) 구현 및 분리
- [x] config(trend_following_config.py) 분리 및 가중치/파라미터 관리
- [x] 전략 본체(trend_following_strategy.py) 완전 분리 및 경로/구조 일관화
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] 상세 로그(info/debug) 추가 및 백테스트/실시간 분석 활용성 강화
- [x] strategy_docs/trend_following_strategy.md 문서화 완료(필요시)
- [x] 커밋 완료

### Market Regime Hybrid 전략
- [x] market_regime_hybrid 폴더/구조 설계 및 생성
- [x] 하위 전략(TrendFollowing, MeanReversion, VolatilityBreakout) 직접 참조 및 인스턴스화
- [x] config(market_regime_hybrid_config.py) 분리 및 파라미터/가중치 관리
- [x] 전략 본체(market_regime_hybrid_strategy.py) 완전 분리 및 경로/구조 일관화
- [x] 팩토리/매니저 import 경로 및 implementation_class 경로 일괄 수정
- [x] 상세 로그(info/debug) 추가 및 백테스트/실시간 분석 활용성 강화
- [x] strategy_docs/market_regime_hybrid_strategy.md 문서화 완료
- [x] 주석 리팩토링 및 커밋 완료

---

## 5. 향후 TODO 및 관리 팁

- [ ] 모든 전략에 대해 단위/통합 테스트 작성 및 검증
- [ ] 신호 근거, 점수, 전략별 동작에 대한 리포트/로그 체계화
- [ ] 문서화(README, 구조/확장법, 예시 등) 및 자동화 스크립트 추가
- [ ] 신규 전략/Detector 추가 시, 기존 구조/패턴을 준수하여 일관성 유지
- [ ] 레거시 코드(domain/analysis/strategy/implementations 등) 일괄 삭제 및 정리 (전략별 폴더 독립화 100% 완료 후)

---

**컨텍스트가 길어질 경우, 이 문서만 최신화하여 관리하면 전체 진행상황과 계획을 한눈에 파악할 수 있습니다.** 

### 전략별 폴더 독립화 이후 기존 코드 정리/수정 계획

1. domain/analysis/strategy/implementations/, domain/analysis/detectors/ 등 상위 디렉터리의 레거시 전략/Detector/config 파일 삭제 또는 deprecated 처리
2. StrategyFactory, StrategyManager 등 전략 생성/등록/선택 로직의 import 경로를 새로운 구조(domain/strategies/전략명/...)로 일괄 수정
3. 테스트 코드의 import 경로 및 테스트 대상 파일/클래스 위치를 모두 새로운 구조로 변경
4. README, 개발 가이드, 예시 코드 등 문서에서 전략 구조/사용법을 새로운 구조로 일원화
5. 중복/불필요/레거시 코드 일괄 삭제 및 deprecated 안내
6. 자동화/배포/테스트 스크립트 등에서 전략 관련 경로를 모두 새로운 구조로 반영

> 이 작업은 모든 전략의 폴더 독립화가 완료된 후 일괄적으로 진행됩니다. 