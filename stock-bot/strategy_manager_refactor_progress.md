# StrategyManager 역할 분리 및 strategy 폴더 폐기 리팩토링 진행상황 (2024-07-09)

## 🎯 목표
- StrategyManager의 과도한 역할을 Static/Mix/Dynamic 매니저로 분리
- 오케스트레이터(StrategyOrchestrator) 도입으로 각 매니저 위임 구조 확립
- domain/analysis/strategy/ 폴더 완전 폐기 및 코드 일관성 확보
- **전략 config 파일(설정)도 각 전략 폴더로 완전 통합/분산, 중복/불일치 해소**

## 🛠️ [재정립] 단계별 플랜 및 안전한 실행 순서 (상세 작업단위)

### 1. 설계/분류/테스트 확보
- [ ] 전체 리팩토링 목표/범위/완료 기준 명확화
- [ ] 기존 strategy_manager.py, config, job 등 주요 파일/클래스 역할 목록화
- [ ] Static/Mix/Dynamic 매니저, Orchestrator, 서비스별 책임/인터페이스 설계서 작성
- [ ] 기존 테스트/샘플 코드 목록화 및 동작 확인
- [ ] 리팩토링 전 전체 시스템 정상 동작 스냅샷 확보

### 2. config/model 분리/이관(독립적, 롤백 쉬움)
- [ ] StrategyConfig, DetectorConfig 등 공통 dataclass/model를 base/models/로 이동
- [ ] StrategyType, StrategyMixMode 등 공통 Enum/type도 base/models/로 이동
- [ ] 각 전략 폴더(configs/)에 개별 config 파일 생성 및 기존 config 내용 이관
- [ ] 믹스 전략도 각 믹스 폴더(configs/)로 config 이관
- [ ] 기존 static_strategies.py, strategy_mixes.py는 deprecated 안내만 남기고 유지
- [ ] 각 전략 config에서 공통 model/type import로 일원화
- [ ] 기존 config와 개별 config의 중복/불일치 해소(값/설명/경로 등)
- [ ] 이관 후 기존 동작/테스트 정상 확인

### 3. 전략 매니저/팩토리 분리
- [ ] StaticStrategyManager, StrategyMixManager, DynamicStrategyManager, Orchestrator 등 파일/클래스 생성
- [ ] 기존 strategy_manager.py 기능을 역할별로 분리/이관(정적/믹스/동적/공통)
- [ ] 각 매니저별 단위 테스트 작성 및 동작 확인
- [ ] 기존 인터페이스/테스트 유지하며 점진적 전환(기존 코드와 병행)
- [ ] 실패시 기존 manager로 롤백 가능하도록 브랜치/PR 관리

### 4. 실시간 Job 역할별 서비스화(점진적, 병렬 가능)
- [ ] DataPreparationService: 데이터 로딩, 캐싱, 전처리, 지표 계산 등만 담당
- [ ] StrategyExecutionService: 전략 모드별(정적/동적/믹스) 신호 감지/실행만 담당
- [ ] SignalPersistenceService: 신호/지표 저장, DB 연동만 담당
- [ ] (선택) SignalDetectionCache: 캐시/상태 관리 전담 객체
- [ ] 기존 realtime_signal_detection_job.py에서 각 서비스로 기능별 코드 점진적 이관
- [ ] 각 서비스별 단위 테스트 작성 및 동작 확인
- [ ] Job(엔트리포인트)에서는 각 서비스 조합/실행만 담당하도록 리팩토링
- [ ] 실패시 기존 Job 구조로 복귀 가능하도록 관리

### 5. 오케스트레이터 통합/외부 인터페이스 정비
- [ ] Orchestrator에서 각 매니저/서비스 위임 구조 확립(코드/다이어그램)
- [ ] 외부에서는 Orchestrator만 사용하도록 인터페이스/문서/테스트 일괄 변경
- [ ] 기존 테스트/실행 코드에서 Orchestrator로 교체(점진적 적용)
- [ ] 실패시 기존 매니저/서비스 직접 사용 가능하도록 브랜치/PR 관리

### 6. 레거시 삭제/경로 정비
- [ ] domain/analysis/strategy/ 폴더 등 레거시 코드/경로 일괄 삭제(최종 단계)
- [ ] 모든 import 경로를 새로운 구조로 일괄 변경(자동화 스크립트 활용)
- [ ] __init__.py, README, 문서 등도 최신화(구조/사용법/확장법)
- [ ] 이 단계는 모든 이전 단계가 안정화된 후 일괄 진행(실패시 git revert 등으로 복구)

### 7. 통합 테스트/문서화
- [ ] 전체 통합 테스트/시나리오 테스트로 최종 검증(실제 데이터/실행 환경)
- [ ] 리팩토링/구조 변경 내역 상세 문서화(변경점, 마이그레이션 가이드)
- [ ] 신규 구조/사용법/확장법 가이드 작성(예시/다이어그램 포함)
- [ ] 성능/동시성/확장성 최적화(프로파일링, 병목 개선 등)

---

> 각 작업단위는 독립적으로 진행/테스트/롤백이 가능하도록 쪼개며, 실패시 영향 최소화와 복구 용이성을 최우선으로 고려합니다.

---

### [정책/계획] 전략 config 파일 통합/분산

- 모든 전략/믹스의 config는 해당 전략/믹스 폴더 내부(configs/)에만 존재하도록 통합
- 중앙 config(static_strategies.py, strategy_mixes.py)는 deprecated 안내만 남기고 점진적으로 폐기
- 매니저/팩토리 등은 각 전략 폴더의 config만 참조(import)하도록 구조 변경
- **config 파일 내 model/dataclass(StrategyConfig, DetectorConfig 등)는 base/models/ 등 공통 위치로 이동, 각 전략 config에서는 import만 사용**
- 공통 Enum/Type/Dataclass(StrategyType, StrategyConfig 등)는 base/에 위치, 각 전략 config에서 import
- 기존 중앙 config에서만 존재하는 전략/설정은 해당 전략 폴더에 새로 만들어 이관
- config 이관/통합 후, 중복/불일치 해소 및 폴더 독립성/확장성/유지보수성 극대화 

---

## [서비스 패키지 구조 결정 및 위치]

### ✅ 서비스 생성 위치: domain/analysis/service/
- DataPreparationService, StrategyExecutionService, SignalPersistenceService 등은 모두 `domain/analysis/service/` 하위에 생성
- 기존 signal_detection_service.py 등과 함께 관리, 분석(analysis) 도메인에 집중
- 스케줄러/잡, API, 백테스트 등 다양한 실행 환경에서 재사용 용이

### [이유 및 장점]
- 분석(Analysis) 도메인에 전략/신호/지표 등 모든 분석 관련 로직이 응집
- 기존 구조와 일관성, 유지보수/확장성/재사용성 모두 우수
- 전략 시스템이 analysis의 하위 개념일 때 가장 자연스러운 구조
- 필요시 하위 폴더로 더 세분화도 가능

### [구조 예시]
```
domain/
  analysis/
    service/
      data_preparation_service.py
      strategy_execution_service.py
      signal_persistence_service.py
      signal_detection_cache.py
      signal_detection_service.py  # 기존 파일
    ...
```

> 서비스별 책임/인터페이스 설계 시 기존 signal_detection_service.py와의 역할 분담/중복 여부도 점검할 것

---

## [실행 플랜] 실시간 신호 감지 Job(및 전략 시스템) 리팩토링

### 1. 역할별 서비스/클래스 분리 설계
- [ ] SignalDetectionJob(오케스트레이터/엔트리포인트): 전체 실행 흐름만 담당, 세부 로직 위임
- [ ] DataPreparationService: 데이터 로딩, 캐싱, 전처리, 지표 계산 등만 담당
- [ ] StrategyExecutionService: 전략 모드별(정적/동적/믹스) 신호 감지/실행만 담당
- [ ] SignalPersistenceService: 신호/지표 저장, DB 연동만 담당
- [ ] (선택) SignalDetectionCache: 캐시/상태 관리 전담 객체

### 2. 기존 Job 기능별 코드 이관 및 서비스화
- [ ] 데이터 준비/캐싱/지표 계산 로직 → DataPreparationService로 이동
- [ ] 전략 시스템 분기/실행/폴백 로직 → StrategyExecutionService로 이동
- [ ] 신호/지표 저장 로직 → SignalPersistenceService로 이동
- [ ] 전역 캐시/상태 관리 → SignalDetectionCache 등으로 이동
- [ ] Job(엔트리포인트)에서는 각 서비스 조합/실행만 담당

### 3. 전략 시스템 연동 구조 개선
- [ ] 전략 config/매니저/팩토리 구조와 연동(의존성 주입, 단방향 참조)
- [ ] Job에서는 config/매니저를 단순 참조, 전략 시스템 변경 시 영향 최소화
- [ ] 폴백/예외/로깅 등은 Decorator/핸들러로 일원화

### 4. 비동기/동기 일관성 확보
- [ ] 전체를 async로 통일하거나, sync/async 경계 명확화
- [ ] 서비스별로 일관된 실행 방식 적용

### 5. 테스트/문서화/최적화
- [ ] 각 서비스/클래스 단위 테스트 작성
- [ ] 리팩토링/구조 변경 내역 문서화
- [ ] 신규 구조/사용법/확장법 가이드 작성
- [ ] 성능/동시성/확장성 최적화

---

### [기대 효과]
- 각 책임별 코드가 분리되어 가독성/유지보수성/테스트 용이
- 전략 시스템 확장/변경 시 Job 코드 영향 최소화
- 캐시/상태 관리 일원화로 동시성/성능 개선
- 예외/로깅/폴백 일관성 확보
- 실시간 신호 감지 시스템의 확장성/안정성/성능 극대화 

### [1단계] 주요 파일/클래스 역할 목록화 (2024-07-09)

| 파일명 | 주요 역할 |
|--------|-----------------------------------------------------------------------------------------------------------------------------------|
| strategy_manager.py | 정적/믹스/동적 전략 전체 관리, 전략 초기화/전환/분석/조합, 오케스트레이션, 동적 전략 위임(DynamicStrategyManager) |
| strategy_factory.py | 정적/동적 전략 인스턴스 생성, config 기반 팩토리, 의존성 주입, 전략 지원 여부 확인, 전략 목록 반환 등 |
| static_strategies.py | StrategyType Enum, StrategyConfig/DetectorConfig dataclass, 각 전략별 config, 전략 config 조회 함수 등 |
| strategy_mixes.py | StrategyMixMode Enum, StrategyMixConfig dataclass, 전략 믹스 config(현재는 각 믹스 폴더에서 관리), 시장상황별 권장 믹스, 조회 함수 등 |
| service/signal_detection_service.py | 신호 감지 서비스, 전략 매니저(StrategyManager) 기반 신호 분석/전략 전환/조합, 지표 캐시, 동적 전략/믹스 지원 |
| run_backtest.py | 백테스팅 실행 스크립트, 다양한 전략/조합/비교/자동선택 백테스트, 결과 요약/저장/출력 |

#### 역할 요약 상세
- **strategy_manager.py**: 정적/믹스/동적 전략의 초기화, 등록, 교체, 분석 실행, 결과 조합 등 모든 전략 관련 오케스트레이션을 담당하며, 동적 전략 관리는 DynamicStrategyManager에 위임함.
- **strategy_factory.py**: 정적/동적 전략 인스턴스 생성의 통합 팩토리로, 전략 타입 ↔️ 전략 클래스 매핑 및 config 기반 생성, 의존성 주입, 여러 전략 동시 생성, 지원 여부 확인 등 부가 기능 제공.
- **static_strategies.py**: 모든 정적 전략의 타입(StrategyType Enum), 각 전략/탐지기의 설정 구조(dataclass), 실제 config, 전략 config 조회/목록 반환 함수 등 제공.
- **strategy_mixes.py**: 전략 조합 방식(Enum), 조합 설정(dataclass), 시장 상황별 권장 믹스, 믹스 config(현재는 각 믹스 폴더에서 관리), 조회 함수 등 제공. 

#### 역할 요약 상세 (추가)
- **service/signal_detection_service.py**: StrategyManager를 활용해 신호 감지, 전략 전환, 믹스/동적 전략 지원, 지표 프리컴퓨팅/캐시, 신호 분석 결과 반환 등 실시간/배치 신호 분석의 핵심 서비스 역할.
- **run_backtest.py**: 다양한 전략/조합/비교/자동선택 모드로 백테스트를 실행하고, 결과를 요약/출력/저장하는 엔트리포인트 스크립트. 실험/비교/리포트 자동화에 활용됨. 

### [1단계] 매니저/서비스/오케스트레이터 책임/인터페이스 설계 (2024-07-09)

| 클래스/서비스명                | 주요 책임/역할                                                                                   | 주요 메서드/인터페이스(예상)                       |
|-------------------------------|--------------------------------------------------------------------------------------------------|---------------------------------------------------|
| StaticStrategyManager         | 정적 전략(Static) 관리, 초기화, 분석, 등록/제거, 상태 관리                                        | initialize(), analyze(), add_strategy(), ...      |
| StrategyMixManager            | 믹스 전략(Mix) 관리, 조합 실행, 결과 통합, 믹스 config 관리                                       | set_mix(), analyze_mix(), get_mix_config(), ...   |
| DynamicStrategyManager        | 동적 전략(Dynamic) 관리, 실시간 가중치 조정, 전략 전환, 상태 관리                                 | initialize(), switch_strategy(), analyze(), ...   |
| Orchestrator (예: SignalDetectionOrchestrator) | 각 매니저/서비스 위임, 전체 실행 흐름 제어, 신호/전략 조율                                      | add_manager(), run(), get_results(), ...          |
| DataPreparationService        | 데이터 로딩, 캐싱, 전처리, 지표 계산 등 데이터 준비 전담                                          | load_data(), compute_indicators(), ...            |
| StrategyExecutionService      | 전략 실행(정적/동적/믹스), 신호 감지, 전략별 분석 실행                                           | execute_strategy(), execute_mix(), ...            |
| SignalPersistenceService      | 신호/지표 저장, DB 연동, 결과 기록                                                               | save_signal(), save_indicator(), ...              |
| SignalDetectionService        | StrategyManager 기반 신호 감지, 전략 전환/조합, 지표 캐시, 동적 전략/믹스 지원                   | initialize(), analyze_with_current_strategy(), ...|

#### 역할/인터페이스 상세 설명
- **StaticStrategyManager**: 정적 전략만을 관리하며, 전략의 초기화, 분석, 추가/제거, 상태 조회 등 책임.
- **StrategyMixManager**: 여러 정적 전략을 조합(가중치, 투표 등)하여 믹스 전략을 실행, 믹스 config 관리.
- **DynamicStrategyManager**: 동적 전략(시장 상황/지표 기반 실시간 가중치 조정) 관리, 전략 전환, 분석 실행.
- **Orchestrator**: 각 매니저/서비스를 조합하여 전체 신호 감지/전략 실행 흐름을 제어, 결과 통합.
- **DataPreparationService**: 데이터 로딩, 전처리, 지표 계산 등 데이터 준비만 전담.
- **StrategyExecutionService**: 전략 실행(정적/동적/믹스) 및 신호 감지, 분석 실행.
- **SignalPersistenceService**: 신호/지표/분석 결과의 저장, DB 연동, 기록 관리.
- **SignalDetectionService**: StrategyManager를 활용한 신호 감지, 전략 전환/조합, 지표 캐시, 실시간/배치 신호 분석의 핵심 서비스. 