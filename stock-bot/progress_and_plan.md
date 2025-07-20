# Stock-Bot 프로젝트 리팩토링 진행 상황

## 전체 계획 (Phase 1-4)

### Phase 1: 기반 구조 설정 (Foundation) ✅ **완료**
- [x] 디렉토리 신설: `application/`, `domain/indicators/`
- [x] 파일 이동: `main.py` → `application/main.py`
- [x] 파일 삭제: 최상위 `run_backtest.py`
- [x] Indicators 계층 구성: `domain/indicators/calculator.py`, `models.py`
- [x] Utils 디렉토리 삭제: `domain/signals/utils/`

### Phase 2: signals 계층 단순화 (Simplification) 🔄 **진행 중**

> **목표**: 여러 전략에 흩어져 있던 신호 감지 및 근거 도출 로직을 중앙화하고 재사용 가능한 부품으로 만드는 것

#### 2.1 detectors 리팩토링 및 일반화 ✅ **부분 완료**
- [x] **strategies 내부 detectors 삭제**: 11개 전략의 `strategies/single/*/detectors/` 디렉토리 삭제
  - [x] aggressive/detectors/ 삭제
  - [x] balanced/detectors/ 삭제  
  - [x] conservative/detectors/ 삭제
  - [x] momentum/detectors/ 삭제
  - [x] mean_reversion/detectors/ 삭제
  - [x] scalping/detectors/ 삭제
  - [x] swing/detectors/ 삭제
  - [x] trend_following/detectors/ 삭제
  - [x] trend_pullback/detectors/ 삭제
  - [x] volatility_breakout/detectors/ 삭제
  - [x] multi_timeframe/detectors/ 삭제
- [x] **중앙 detectors 일반화**: 주요 Detector들에 파라미터 주입 방식 적용
  - [x] `SMASignalDetector` - 파라미터 주입 방식 적용
  - [x] `VolumeSignalDetector` - 파라미터 주입 방식 적용
  - [x] `RSISignalDetector` - 파라미터 주입 방식 적용
  - [x] `ADXSignalDetector` - 파라미터 주입 방식 적용
  - [ ] `StochSignalDetector` - 파라미터 주입 방식 적용 예정
  - [ ] `MACDSignalDetector` - 파라미터 주입 방식 적용 예정
  - [ ] `BBSignalDetector` - 파라미터 주입 방식 적용 예정
- [x] **전략 업데이트**: 커스텀 Detector 대신 중앙 Detector 사용
  - [x] `AggressiveStrategy` - 중앙 Detector + 파라미터 사용
  - [x] `BalancedStrategy` - 중앙 Detector + 파라미터 사용
  - [ ] 나머지 9개 전략 업데이트 예정

#### 2.2 analysis 패키지 신설 (확장 가능한 분석 로직) 🔄 **진행 중**
> **목표**: 기존 CompositeDetector 등에 흩어져 있던 복합 분석 로직을 성격에 맞는 파일로 분리하여 함수로 관리

- [x] **analysis 패키지 생성**: `domain/signals/analysis/` 디렉토리 생성
- [x] **분석 로직 분리**: 
  - [x] `momentum.py` - RSI, Stoch, MACD 조합 분석 (✅ 완료)
    - ✅ `MomentumConsensus` Enum 정의
    - ✅ `get_momentum_consensus()` - RSI, Stochastic, MACD 종합 분석
    - ✅ `analyze_rsi_stoch_condition()` - RSI+Stoch 조합 상태 분석
  - [x] `volume.py` - MACD와 거래량 조합 분석 (✅ 완료)
    - ✅ `MacdVolumeEvidence` Enum 정의
    - ✅ `analyze_macd_with_volume()` - MACD+거래량 조합 분석
    - ✅ `get_volume_pattern()` - 거래량 패턴 분석
  - [ ] `trend.py` - SMA, MACD, ADX 추세 분석 (🔄 **예정**)
    ```python
    # 예시 구조 (사용자 제공)
    class MacdEvidence(Enum):
        GOLDEN_CROSS = "MACD 골든크로스"
        DEAD_CROSS = "MACD 데드크로스"
    
    def analyze_macd_cross(data: pd.DataFrame) -> MacdEvidence | None:
        """MACD 지표를 분석하여 크로스오버 근거를 반환합니다."""
    ```
  - [ ] `volatility.py` - BB, ADX 변동성 분석 (🔄 **예정**)
- [ ] **CompositeDetector 로직 이전**: 기존 복합 분석 로직을 해당 파일의 함수로 이전

#### 2.3 rules 패키지 신설 (확장 가능한 결정 로직) 🔜 **대기**
> **목표**: 재사용 가능한 규칙들을 파일별로 그룹화하고 하나의 RULES 딕셔너리로 통합

- [ ] **rules 패키지 생성**: `domain/signals/rules/` 디렉토리 생성
- [ ] **규칙 로직 분리**:
  - [ ] `momentum.py` - 모멘텀 관련 규칙
    ```python
    # 예시 구조
    MOMENTUM_RULES = {
        'rsi_stoch_oversold_consensus': 
            lambda data: get_oversold_consensus(data) == MomentumConsensus.STRONG_BULLISH,
    }
    ```
  - [ ] `trend.py` - 추세 관련 규칙 (🔄 **사용자 예시 제공**)
    ```python
    # 예시 구조 (사용자 제공)
    TREND_RULES = {
        'macd_confirms_golden_cross':
            lambda data: analyze_macd_cross(data) == MacdEvidence.GOLDEN_CROSS,
        'macd_confirms_dead_cross':
            lambda data: analyze_macd_cross(data) == MacdEvidence.DEAD_CROSS,
    }
    ```
  - [ ] `volume.py` - 거래량 관련 규칙
  - [ ] `volatility.py` - 변동성 관련 규칙
- [ ] **RULES 딕셔너리 통합**: `rules/__init__.py`에서 모든 규칙 통합 (🔄 **사용자 예시 제공**)
  ```python
  # 예시 구조 (사용자 제공)
  from .momentum import MOMENTUM_RULES
  from .trend import TREND_RULES
  
  RULES = {
      **MOMENTUM_RULES,
      **TREND_RULES,
  }
  ```

#### 2.4 불필요한 코드 제거 🔜 **대기**
- [ ] **service 디렉토리 삭제**: `domain/signals/service/` 삭제
- [ ] **config 디렉토리 삭제**: `domain/signals/config/` 삭제

#### 2.5 모델 통합 🔜 **대기**
- [ ] **models 통합**: `domain/signals/models/` 내 파일들을 단일 `models.py`로 통합
  - [ ] `enums/` 디렉토리 내용 통합
  - [ ] `strategy_result.py` 통합
  - [ ] `technical_indicator.py` 통합
  - [ ] 기타 모델 파일들 통합

### Phase 3: strategies 계층 YAML 기반 재구성 (Strategy Redesign) 🔜 **Phase 2 완료 후 진행 여부 확인**
- [ ] YAML 전략 정의 스키마 설계
- [ ] 전략 해석기 구현
- [ ] 기존 전략들을 YAML로 마이그레이션

### Phase 4: services 계층 및 최종 정리 (Service Layer & Finalization) 🔜 **대기**
- [ ] domain/services 계층 신설
- [ ] 유스케이스 정의 및 구현
- [ ] 최종 테스트 및 문서화

---

## Phase 2 진행 상황 상세

### 🎯 주요 성과
1. **✅ Detector 중앙화 완료**: 모든 전략의 개별 detectors 디렉토리 제거
2. **✅ 파라미터 주입 시스템 구축**: 4개 주요 Detector에 설정 외부화 적용
3. **✅ Analysis 패키지 기반 구축**: momentum, volume 분석 모듈 완성
4. **✅ 전략 현대화**: aggressive, balanced 전략의 중앙 Detector 전환 완료

### 🔧 적용된 파라미터 주입 예시
```python
# 공격적 전략용 SMA 파라미터
aggressive_sma_params = {
    'adx_threshold': 15,  # 기본 20에서 더 민감하게
    'continuation_weight': 0.6,  # 기본 0.4에서 더 적극적으로
    'trend_confirmation_required': False  # 추세 확인 불필요
}

# 중앙 Detector 사용
SMASignalDetector(
    weight=self.config.detector_weights['sma'],
    name="Aggressive_SMA_Detector",
    parameters=aggressive_sma_params
)
```

### 📦 현재 Analysis 모듈 구조
```
domain/signals/analysis/
├── __init__.py
├── momentum.py     # ✅ 완성: 모멘텀 컨센서스, RSI-Stoch 조합 분석
├── volume.py       # ✅ 완성: MACD-거래량 조합, 거래량 패턴 분석
├── trend.py        # 🔄 예정: MACD 크로스, SMA 추세 분석
└── volatility.py   # 🔄 예정: BB 변동성, ADX 조합 분석
```

### 📋 계획된 Rules 모듈 구조 (사용자 예시 기반)
```
domain/signals/rules/
├── __init__.py     # 모든 규칙 RULES 딕셔너리로 통합
├── momentum.py     # 모멘텀 관련 규칙 함수들
├── trend.py        # 추세 관련 규칙 함수들 (MACD 크로스 등)
├── volume.py       # 거래량 관련 규칙 함수들
└── volatility.py   # 변동성 관련 규칙 함수들
```

### 🚀 다음 단계 우선순위
1. **analysis/trend.py 구현**: 사용자 제공 예시에 따른 MACD 크로스 분석
2. **analysis/volatility.py 구현**: BB, ADX 변동성 분석
3. **rules 패키지 전체 구현**: 사용자 예시에 따른 규칙 딕셔너리 구조
4. **나머지 Detector 파라미터화**: StochSignalDetector, MACDSignalDetector, BBSignalDetector
5. **나머지 전략 업데이트**: 9개 전략의 중앙 Detector 전환
6. **불필요한 코드 제거**: service, config 디렉토리 정리
7. **모델 통합**: models/ 파일들 단일화

### 💡 Phase 2의 핵심 가치

1. **📍 관심사 분리**: 분석 로직(analysis) ↔ 결정 로직(rules) ↔ 감지 로직(detectors)
2. **🔄 재사용성**: 함수 기반 모듈로 전략 간 로직 공유
3. **🎛️ 설정 외부화**: 파라미터 주입으로 전략별 특화 가능
4. **📈 확장성**: 새로운 분석/규칙 추가 시 기존 구조 활용

---

## 작업 시작일
- **Phase 2 시작**: 2025-01-XX
- **현재 진행률**: Phase 2의 약 40% 완료

## 중요 참고사항
- ✅ 파라미터 주입 방식으로 전략별 특화 설정 가능
- ✅ Analysis 모듈로 복합 분석 로직 중앙화
- 🔄 **Phase 3 시작 전 진행 여부 확인 필요** ⚠️
- 🔄 Import 경로 정리 및 의존성 확인 지속 진행
- 🔄 기존 기능 유지하면서 점진적 리팩토링 진행 