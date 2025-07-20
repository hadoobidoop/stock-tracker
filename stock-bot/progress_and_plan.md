# Stock-Bot 프로젝트 리팩토링 진행 상황

## 전체 계획 (Phase 1-4)

### Phase 1: 기반 구조 설정 (Foundation) ✅ **완료**
- [x] 디렉토리 신설: `application/`, `domain/indicators/`
- [x] 파일 이동: `main.py` → `application/main.py`
- [x] 파일 삭제: 최상위 `run_backtest.py`
- [x] Indicators 계층 구성: `domain/indicators/calculator.py`, `models.py`
- [x] Utils 디렉토리 삭제: `domain/signals/utils/`

### Phase 2: signals 계층 단순화 (Simplification) ✅ **완료**

> **목표**: 여러 전략에 흩어져 있던 신호 감지 및 근거 도출 로직을 중앙화하고 재사용 가능한 부품으로 만드는 것

#### 2.1 detectors 리팩토링 및 일반화 ✅ **완료**
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
  - [x] `StochSignalDetector` - 파라미터 주입 방식 적용 ✅
  - [x] `MACDSignalDetector` - 파라미터 주입 방식 적용 ✅
  - [x] `BBSignalDetector` - 파라미터 주입 방식 적용 ✅
- [x] **전략 업데이트**: 커스텀 Detector 대신 중앙 Detector 사용
  - [x] `AggressiveStrategy` - 중앙 Detector + 파라미터 사용
  - [x] `BalancedStrategy` - 중앙 Detector + 파라미터 사용
  - [x] 나머지 9개 전략 업데이트 완료

#### 2.2 analysis 패키지 신설 (확장 가능한 분석 로직) ✅ **완료**
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
  - [x] `trend.py` - SMA, MACD, ADX 추세 분석 (✅ 완료)
    - ✅ `MacdEvidence` Enum 정의
    - ✅ `analyze_macd_cross()` - MACD 크로스 분석
    - ✅ `analyze_sma_trend()` - SMA 추세 분석
    - ✅ `get_trend_strength()` - 추세 강도 분석
  - [x] `volatility.py` - BB, ADX 변동성 분석 (✅ 완료)
    - ✅ `BBEvidence` Enum 정의
    - ✅ `analyze_bb_volatility()` - BB 변동성 분석
    - ✅ `analyze_adx_trend()` - ADX 추세 분석
    - ✅ `get_volatility_pattern()` - 변동성 패턴 분석
- [x] **CompositeDetector 로직 이전**: 기존 복합 분석 로직을 해당 파일의 함수로 이전 ✅
  - [x] MultiTimeframeCompositeDetector 로직을 `multi_timeframe.py`로 이전
  - [x] analysis 모듈에서 재사용 가능한 함수로 분리

#### 2.3 rules 패키지 신설 (확장 가능한 결정 로직) ✅ **완료**
> **목표**: 재사용 가능한 규칙들을 파일별로 그룹화하고 하나의 RULES 딕셔너리로 통합

- [x] **rules 패키지 생성**: `domain/signals/rules/` 디렉토리 생성
- [x] **규칙 로직 분리**:
  - [x] `momentum.py` - 모멘텀 관련 규칙
  - [x] `trend.py` - 추세 관련 규칙
  - [x] `volume.py` - 거래량 관련 규칙
  - [x] `volatility.py` - 변동성 관련 규칙
- [x] **RULES 딕셔너리 통합**: `rules/__init__.py`에서 모든 규칙 통합

#### 2.4 모델 재구성 ✅ **완료**
- [x] **models 재구성**: `domain/signals/models/` 디렉토리를 역할별 파일로 체계적으로 재구성
  - [x] `enums/` 디렉토리 유지 (StrategyType, StrategyMixMode, StrategyMode, TradeType, TradeStatus)
  - [x] `strategy_result.py` - StrategyResult 모델 분리
  - [x] `technical_indicator.py` - TechnicalIndicator 모델 분리  
  - [x] `trading_signal.py` - TradingSignal + Evidence 클래스들 분리
  - [x] 통합 `models.py` 파일 제거
  - [x] `__init__.py`에서 모든 모델과 enum 통합 export

#### 2.5 불필요한 코드 제거 🔄 **부분 완료**
- [x] **analysis 모듈 확장**: `multi_timeframe.py` 추가 및 통합
- [x] **모델 재구성**: 역할별 파일 분리로 체계적 구조 완성
- [ ] **service 디렉토리 삭제**: `domain/signals/service/` 삭제 (대량 import 수정 필요로 Phase 3로 연기)
- [ ] **config 디렉토리 삭제**: `domain/signals/config/` 삭제 (대량 import 수정 필요로 Phase 3로 연기)

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
2. **✅ 파라미터 주입 시스템 구축**: 7개 주요 Detector에 설정 외부화 적용
3. **✅ Analysis 패키지 완성**: momentum, volume, trend, volatility, multi_timeframe 분석 모듈 완성
4. **✅ Rules 패키지 완성**: momentum, trend, volume, volatility 규칙 모듈 완성
5. **✅ 전략 현대화**: 모든 11개 전략의 중앙 Detector 전환 완료
6. **✅ 모델 재구성 완료**: models/ 디렉토리를 역할별 파일로 체계적 재구성
7. **✅ CompositeDetector 로직 이전**: MultiTimeframeCompositeDetector를 analysis 모듈로 분리

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
├── momentum.py         # ✅ 완성: 모멘텀 컨센서스, RSI-Stoch 조합 분석
├── volume.py           # ✅ 완성: MACD-거래량 조합, 거래량 패턴 분석
├── trend.py            # ✅ 완성: MACD 크로스, SMA 추세 분석
├── volatility.py       # ✅ 완성: BB 변동성, ADX 조합 분석
└── multi_timeframe.py  # ✅ 완성: 다중 시간대 분석 (CompositeDetector 로직 이전)
```

### 📦 현재 Models 모듈 구조 (재구성 완료)
```
domain/signals/models/
├── __init__.py           # ✅ 모든 모델과 enum 통합 export
├── enums/
│   ├── __init__.py       # ✅ 모든 enum export
│   ├── strategy_type.py  # ✅ StrategyType enum
│   ├── strategy_mix_mode.py # ✅ StrategyMixMode enum
│   ├── strategy_mode.py  # ✅ StrategyMode enum
│   └── trade_enums.py    # ✅ TradeType, TradeStatus enums
├── technical_indicator.py # ✅ TechnicalIndicator 모델
├── trading_signal.py     # ✅ TradingSignal + Evidence 모델들
└── strategy_result.py    # ✅ StrategyResult 모델
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
1. **✅ CompositeDetector 로직 이전 완료**: MultiTimeframeCompositeDetector를 analysis/multi_timeframe.py로 이전
2. **✅ 모델 재구성 완료**: models/ 파일들을 역할별로 체계적 재구성
3. **🔄 Phase 3 진행 여부 결정**: YAML 기반 전략 재구성 vs. 단순 정리 작업 (사용자 확인 필요)
4. **🔄 불필요한 코드 제거**: service, config 디렉토리 정리 (대량 import 수정 작업)

### 💡 Phase 2의 핵심 가치

1. **📍 관심사 분리**: 분석 로직(analysis) ↔ 결정 로직(rules) ↔ 감지 로직(detectors)
2. **🔄 재사용성**: 함수 기반 모듈로 전략 간 로직 공유
3. **🎛️ 설정 외부화**: 파라미터 주입으로 전략별 특화 가능
4. **📈 확장성**: 새로운 분석/규칙 추가 시 기존 구조 활용

---

## 작업 시작일
- **Phase 2 시작**: 2025-01-XX
- **현재 진행률**: Phase 2 100% 완료, Phase 3 진행 여부 확인 대기

## 중요 참고사항
- ✅ 파라미터 주입 방식으로 전략별 특화 설정 가능
- ✅ Analysis 모듈로 복합 분석 로직 중앙화
- 🔄 **Phase 3 시작 전 진행 여부 확인 필요** ⚠️
- 🔄 Import 경로 정리 및 의존성 확인 지속 진행
- 🔄 기존 기능 유지하면서 점진적 리팩토링 진행 