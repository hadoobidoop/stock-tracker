# Stock Analyzer Bot 📈

주식 기술적 분석 및 자동 신호 감지를 위한 고급 전략 시스템

## 🎯 통합 전략 시스템 특징

### 3가지 전략 모드 [Stock Bot 프로젝트에는 3가지 전략 시스템이 있습니다: 1) Static Strategy (정적 전략) - 고정된 규칙으로 거래 (CONSERVATIVE, BALANCED, AGGRESSIVE), 2) Dynamic Strategy (동적 전략) - 시장 상황에 따라 가중치가 실시간 변경되는 지능형 전략 (VIX, Fear&Greed 지수 기반), 3) Static Strategy Mix (정적 전략 조합) - 여러 정적 전략을 동시에 실행하여 투표/앙상블 방식으로 결정 (balanced_mix, conservative_mix, aggressive_mix). "레거시"는 "Static Strategy Mix"로 용어 변경됨.][[memory:729585415608458330]]

1. **정적 전략 (Static Strategy)**: 고정된 규칙으로 거래
   - 14가지 전략 지원 (CONSERVATIVE, BALANCED, AGGRESSIVE + 11가지 확장 전략)
   - 각 전략마다 고유한 리스크 프로파일과 지표 조합
   - 예측 가능하고 안정적인 성능

2. **동적 전략 (Dynamic Strategy)**: 시장 상황에 따라 가중치가 실시간 변경
   - VIX, Fear&Greed 지수 등 거시 지표 기반
   - 10개의 스마트 모디파이어로 전략 자동 조정
   - 시장 변동성에 따른 적응형 리스크 관리

3. **Static Strategy Mix**: 여러 정적 전략을 동시에 실행하여 투표/앙상블 방식으로 결정
   - balanced_mix, conservative_mix, aggressive_mix 제공
   - 앙상블 학습 기법으로 단일 전략 한계 극복
   - 다중 전략 합의를 통한 신뢰성 높은 신호

### 전략 선택 시스템
- **환경변수 기반 설정**: 런타임에 전략 모드와 전략 선택 가능
- **자동 폴백**: 동적 전략 실패 시 정적 전략으로 자동 전환
- **Hot-swapping**: 실행 중 전략 변경 지원
- **설정 유연성**: 백테스팅과 실시간 작업에서 각각 다른 전략 사용 가능

### Multi-Strategy Support
- **동적 전략 교체**: 런타임에 전략을 바꿀 수 있는 "Hot-swapping" 지원
- **Static Strategy Mix**: 여러 정적 전략을 조합하여 앙상블 방식으로 분석
- **자동 전략 선택**: 시장 상황에 따라 최적 전략 자동 선택
- **지표 프리컴퓨팅**: 모든 기술적 지표를 미리 계산하여 성능 최적화
- **복합 감지기 설정**: 여러 감지기를 조합하여 더 강력한 신호 생성

### 복합 감지기 시스템
1. **MACD_Volume_Confirm**: MACD + 거래량 신호 조합
2. **RSI_Stoch_Confirm**: RSI + 스토캐스틱 신호 조합
3. **Any_Momentum**: RSI 또는 스토캐스틱 신호
4. **Multi_Confirm**: SMA + MACD 신호 조합

## 📊 투자 전략별 상세 설명

### 1. CONSERVATIVE (보수적 전략)
- **목표**: 안정적이고 신뢰도 높은 수익 추구
- **특징**: 
  - 높은 신호 임계값 (12.0) - 매우 강한 신호만 수용
  - 낮은 리스크 (1%) - 안전한 포지션 크기
  - 복합 신호 중심 - MACD + 거래량 확인 필수
  - 시장 추세 일치 신호만 수용
- **적합한 투자자**: 안정성을 중시하는 장기 투자자
- **보유 기간**: 최대 3일 (72시간)
- **최대 포지션**: 3개

### 2. BALANCED (균형잡힌 전략)
- **목표**: 안정성과 수익성의 균형
- **특징**:
  - 중간 신호 임계값 (8.0) - 적당한 강도의 신호 수용
  - 중간 리스크 (2%) - 표준적인 포지션 크기
  - 다양한 지표 균형 사용 - SMA, MACD, RSI, 거래량, ADX
  - 복합 신호와 단일 신호 모두 활용
- **적합한 투자자**: 대부분의 일반 투자자
- **보유 기간**: 최대 2일 (48시간)
- **최대 포지션**: 5개

### 3. AGGRESSIVE (공격적 전략)
- **목표**: 많은 거래 기회를 통한 높은 수익 추구
- **특징**:
  - 낮은 신호 임계값 (5.0) - 약한 신호도 수용
  - 높은 리스크 (3%) - 큰 포지션 크기
  - 모든 지표 활용 - 개별 신호도 적극 활용
  - OR 조건 복합 신호 - Any_Momentum 사용
- **적합한 투자자**: 높은 위험을 감수할 수 있는 적극적 투자자
- **보유 기간**: 최대 1일 (24시간)
- **최대 포지션**: 8개

### 4. MOMENTUM (모멘텀 전략)
- **목표**: 가격 모멘텀을 활용한 단기 수익
- **특징**:
  - RSI, 스토캐스틱 지표 중심 (높은 가중치)
  - 모멘텀 확인 필터 적용
  - RSI + 스토캐스틱 복합 신호 중시
  - 중간 리스크 (2.5%)
- **적합한 투자자**: 모멘텀 투자를 선호하는 단기 투자자
- **보유 기간**: 1.5일 (36시간)
- **최대 포지션**: 4개

### 5. TREND_FOLLOWING (추세추종 전략)
- **목표**: 명확한 추세를 따라가는 안정적 수익
- **특징**:
  - SMA, MACD, ADX 등 추세 지표 중심
  - 추세 일치 및 강도 확인 필수
  - MACD + 거래량 복합 신호 중시
  - 중간 리스크 (2%)
- **적합한 투자자**: 추세 투자를 선호하는 투자자
- **보유 기간**: 2.5일 (60시간) - 긴 보유
- **최대 포지션**: 4개

### 6. CONTRARIAN (역투자 전략)
- **목표**: 과매수/과매도 구간에서 반전 수익
- **특징**:
  - RSI, 스토캐스틱 등 오실레이터 중심
  - 역추세 신호 탐지
  - 시장 심리 반대 포지션
  - 중간 리스크 (2%)
- **적합한 투자자**: 역발상 투자를 선호하는 경험 있는 투자자
- **보유 기간**: 2일 (48시간)
- **최대 포지션**: 3개

### 7. SCALPING (스캘핑 전략)
- **목표**: 초단기 매매를 통한 작은 수익 반복
- **특징**:
  - 매우 낮은 신호 임계값 (4.0)
  - 거래량 지표 중시 (높은 가중치)
  - 빠른 진입/청산
  - 낮은 리스크 (1.5%)
- **적합한 투자자**: 활발한 단기 매매를 선호하는 투자자
- **보유 기간**: 0.5일 (12시간) - 매우 짧음
- **최대 포지션**: 6개

### 8. SWING (스윙 전략)
- **목표**: 중기 가격 변동을 통한 수익
- **특징**:
  - 복합 신호 중심 - Multi_Confirm 사용
  - SMA + MACD 조합 신호
  - 중간 리스크 (2%)
  - 적당한 보유 기간
- **적합한 투자자**: 중기 투자를 선호하는 투자자
- **보유 기간**: 2일 (48시간)
- **최대 포지션**: 4개

### 9. MEAN_REVERSION (평균 회귀 전략) 🆕
- **목표**: 과매수/과매도 후 평균으로 회귀하는 경향 활용
- **특징**:
  - 볼린저 밴드 기반 평균 회귀 신호
  - RSI, 스토캐스틱으로 과매수/과매도 확인
  - 횡보장에서 효과적
  - 낮은 리스크 (1.5%)
- **적합한 투자자**: 레인지 바운드 시장에서 투자하는 투자자
- **보유 기간**: 1일 (24시간)
- **최대 포지션**: 4개

### 10. TREND_PULLBACK (추세 추종 눌림목 전략) 🆕
- **목표**: 상승 추세 중 일시적 하락(눌림목) 시 매수
- **특징**:
  - 장기 추세 확인 후 단기 눌림목 포착
  - SMA, ADX로 추세 강도 확인
  - RSI로 눌림목 타이밍 포착
  - 중간 리스크 (2%)
- **적합한 투자자**: 추세 지속을 믿는 중기 투자자
- **보유 기간**: 3일 (72시간)
- **최대 포지션**: 4개

### 11. VOLATILITY_BREAKOUT (변동성 돌파 전략) 🆕
- **목표**: 변동성 응축 후 폭발하는 시점 포착
- **특징**:
  - 볼린저 밴드 돌파 신호
  - ADX로 추세 강도 확인
  - 거래량 증가 확인 필수
  - 높은 리스크 (2.5%)
- **적합한 투자자**: 변동성 증가를 활용하려는 투자자
- **보유 기간**: 2일 (48시간)
- **최대 포지션**: 3개

### 12. QUALITY_TREND (고신뢰도 복합 추세 전략) 🆕
- **목표**: 여러 추세 지표가 모두 동의할 때만 진입
- **특징**:
  - SMA + MACD + ADX 모든 지표 합의 필요
  - 매우 높은 신호 임계값 (10.0)
  - 추세 일치와 강도 모두 확인
  - 매우 낮은 리스크 (1%)
- **적합한 투자자**: 확실한 기회만 잡으려는 보수적 투자자
- **보유 기간**: 5일 (120시간)
- **최대 포지션**: 2개

### 13. MULTI_TIMEFRAME (다중 시간대 확인 전략) 🆕
- **목표**: 장기 추세(일봉)와 단기(시간봉) 진입 신호 함께 확인
- **특징**:
  - 다중 시간대 분석
  - MACD, 스토캐스틱, RSI 조합
  - 시간대별 추세 일치 확인
  - 중간 리스크 (2%)
- **적합한 투자자**: 정교한 타이밍을 중시하는 투자자
- **보유 기간**: 4일 (96시간)
- **최대 포지션**: 3개

### 14. MACRO_DRIVEN (거시지표 기반 전략) 🆕
- **목표**: VIX와 버핏지수 등 거시경제 지표를 활용한 시장 타이밍
- **특징**:
  - VIX(공포지수) 기반 시장 심리 분석
  - 버핏지수 기반 시장 밸류에이션 평가
  - 기술적 분석과 거시지표의 스마트 결합
  - 동적 리스크 조정 (VIX 레벨에 따라)
  - 고평가 시장에서 자동 리스크 감소
- **적합한 투자자**: 거시경제를 고려한 투자를 선호하는 투자자
- **보유 기간**: 3일 (72시간)
- **최대 포지션**: 4개
- **핵심 기능**:
  - VIX < 15: 자만 상태, 매수 신호 약화
  - VIX > 30: 공포 상태, 매수 신호 강화
  - 버핏지수 > 120%: 고평가, 매수 신호 30% 감소
  - 버핏지수 < 80%: 저평가, 매수 신호 20% 증가

### Static Strategy Mix 모드
- **SINGLE**: 단일 전략 사용
- **WEIGHTED**: 가중 평균 조합
- **VOTING**: 투표 방식 조합
- **ENSEMBLE**: 앙상블 방식 조합

## ⚙️ 전략 설정 및 선택

### 환경변수로 기본 전략 설정

시스템 기본 전략을 환경변수로 설정할 수 있습니다:

```bash
# 기본 전략 모드 설정 (디폴트: dynamic)
export STRATEGY_MODE=dynamic          # static, dynamic, static_mix 중 선택

# 정적 전략 기본값 설정
export STATIC_STRATEGY=BALANCED       # 정적 전략 사용 시 기본값

# 동적 전략 기본값 설정  
export DYNAMIC_STRATEGY=dynamic_weight_strategy  # 동적 전략 사용 시 기본값

# Static Strategy Mix 기본값 설정
export STRATEGY_MIX=balanced_mix      # Static Strategy Mix 사용 시 기본값

# 폴백 전략 활성화/비활성화
export STRATEGY_FALLBACK=true         # 동적 전략 실패 시 정적 전략으로 폴백
```

### 사용 가능한 전략 확인

```bash
# 모든 전략 목록 확인
python main.py --list-strategies
```

출력 예시:
```
📊 정적 전략 (Static Strategies):
• conservative: 보수적 전략 (임계값: 12.0, 리스크: 1.0%)
• balanced: 균형잡힌 전략 (임계값: 8.0, 리스크: 2.0%)
• aggressive: 공격적 전략 (임계값: 5.0, 리스크: 3.0%)
• momentum: 모멘텀 전략 (임계값: 6.0, 리스크: 2.5%)
... (11가지 확장 전략)

🧠 동적 전략 (Dynamic Strategies):
• dynamic_weight_strategy: Dynamic Weight Strategy
  (임계값: 8.0, 리스크: 2.0%, 모디파이어: 10개)
• conservative_dynamic_strategy: Conservative Dynamic Strategy
• aggressive_dynamic_strategy: Aggressive Dynamic Strategy

🔀 Static Strategy Mix:
• balanced_mix, conservative_mix, aggressive_mix
```

## 🚀 사용법

### 기본 실행
```bash
# 기본 balanced 전략으로 실행
python run_backtest.py --mode strategy --strategy BALANCED --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 특정 전략으로 실행
python run_backtest.py --mode strategy --strategy CONSERVATIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
python run_backtest.py --mode strategy --strategy MOMENTUM --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

### 전략 조합 사용
```bash
# 균형잡힌 조합 전략
python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 보수적 조합 전략
python run_backtest.py --mode strategy-mix --strategy-mix conservative_mix --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 공격적 조합 전략
python run_backtest.py --mode strategy-mix --strategy-mix aggressive_mix --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

### 자동 전략 선택
```bash
# 시장 상황에 따른 자동 전략 선택
python run_backtest.py --mode auto-strategy --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

### 전략 비교
```bash
# 모든 전략 비교
python run_backtest.py --mode strategy-comparison --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01

# 특정 전략들만 비교
python run_backtest.py --mode strategy-comparison --compare-strategies CONSERVATIVE BALANCED AGGRESSIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

## 🎮 전략 데모 실행

전략 시스템의 모든 기능을 체험해볼 수 있는 데모를 제공합니다:

```bash
python strategy_demo.py
```

데모에서 확인할 수 있는 기능:
- 전략 간 실시간 교체
- 전략 조합 및 앙상블
- 모든 전략 동시 분석
- 지표 프리컴퓨팅 성능
- 자동 전략 선택
- 성능 모니터링

## 🔧 고급 사용법

### 복합 감지기 설정

```python
from domain.analysis.config.strategy_settings import StrategyType, CompositeDetectorConfig

# 복합 감지기 설정 예시
composite_config = {
    'MACD_Volume_Confirm': {
        'sub_detectors': ['MACDSignalDetector', 'VolumeSignalDetector']
    },
    'RSI_Stoch_Confirm': {
        'sub_detectors': ['RSISignalDetector', 'StochSignalDetector']
    },
    'Multi_Confirm': {
        'sub_detectors': ['SMASignalDetector', 'MACDSignalDetector']
    }
}

# 전략에 복합 감지기 적용
service.configure_composite_detectors(composite_config)
```

### 프로그래밍 방식 사용

```python
from domain.analysis.service.signal_detection_service import SignalDetectionService
from domain.analysis.config.strategy_settings import StrategyType

# 서비스 초기화
service = SignalDetectionService()
service.initialize()

# 특정 전략으로 분석
result = service.detect_signals_with_strategy(
    df_with_indicators, "AAPL", StrategyType.MOMENTUM
)

# 모든 전략으로 분석
all_results = service.analyze_all_strategies(df_with_indicators, "AAPL")

# 전략 교체
service.switch_strategy(StrategyType.AGGRESSIVE)

# 전략 조합 설정
service.set_strategy_mix("balanced_mix")
```

### 지표 프리컴퓨팅

```python
# 특정 종목의 모든 지표를 미리 계산
df_with_indicators = service.precompute_indicators_for_ticker("AAPL", df)

# 캐시 관리
service.clear_indicator_cache("AAPL")  # 특정 종목 캐시 삭제
service.clear_indicator_cache()        # 모든 캐시 삭제
```

## 📊 모니터링 및 성능

### 성능 지표 확인
```python
# 현재 전략 정보
current_info = service.get_current_strategy_info()

# 사용 가능한 전략 목록
strategies = service.get_available_strategies()

# 전략별 성능 요약
performance = service.get_strategy_performance_summary()
```

### 전략 설정 저장/로드
```python
# 현재 전략 설정 저장
service.save_strategy_configs("./my_strategies.json")

# 전략 설정 로드
service.load_strategy_configs("./my_strategies.json")
```

## 📊 시장 데이터 수집 시스템

### 📈 Buffett Indicator (버핏 지수) 시스템
버핏 지수는 전체 주식시장 시가총액 대비 GDP 비율로, 시장 밸류에이션을 나타내는 핵심 지표입니다.

#### 🔄 이중 데이터 소스 전략
- **1차 데이터 소스**: Federal Reserve Z.1 Financial Accounts (NCBEILQ027S)
  - 공식 미국 연방준비제도 데이터
  - 무제한 API 호출
  - 가장 신뢰성 높은 시가총액 데이터
- **2차 백업 소스**: Yahoo Finance Wilshire 5000 (^W5000)
  - 실시간 데이터 보완
  - API 호출 제한 관리 적용
  - Fed 데이터 장애 시 자동 전환

#### 📊 데이터 수집 및 계산
```python
# 버핏 지수 = (전체 주식시장 시가총액 / GDP) × 100

# Fed Z.1 기반 계산 (기본 방식)
market_cap = fed_z1_data["NCBEILQ027S"] / 1000  # 백만→십억 USD 변환
gdp = fred_data["GDP"]  # 십억 USD
buffett_ratio = (market_cap / gdp) * 100

# Yahoo ^W5000 기반 계산 (백업 방식)
wilshire_points = yahoo_data["^W5000"]["Close"]
estimated_market_cap = wilshire_points * 1.08  # 변환 계수
buffett_ratio = (estimated_market_cap / gdp) * 100
```

#### 🎯 현재 시스템 성능
- **정확도**: Fed Z.1 기준 197.5% (2025년 기준)
- **데이터 범위**: 36년 이상의 역사적 데이터
- **업데이트 주기**: 일일 자동 업데이트
- **백업 성공률**: 100% (Yahoo Finance 연동)

### 🌪️ VIX (변동성 지수) 시스템
VIX는 시장의 공포 및 불안 정도를 나타내는 핵심 지표입니다.

#### 🔄 이중 데이터 소스 전략  
- **1차 데이터 소스**: FRED (VIXCLS)
  - 연방준비제도 경제 데이터
  - 일봉 데이터 제공
- **2차 백업 소스**: Yahoo Finance (^VIX)
  - 실시간 데이터
  - 시간봉/일봉 모두 지원

#### 📈 기타 시장 지표
- **10년 국채 수익률**: FRED DGS10 데이터 활용
- **향후 확장 예정**: Put/Call 비율, Fear & Greed Index 등

### 🛡️ Yahoo Finance API 호출 제한 관리

#### ⚡ 스마트 API 관리 시스템
```python
# API 호출 제한 방지 설정
yahoo_request_delay = 1.0      # 호출 간 최소 1초 지연
yahoo_retry_count = 3          # 최대 3회 재시도
fred_preferred = True          # FRED 우선 사용

# 지능적 지연 관리
delay = base_delay + random.uniform(-0.2, 0.2)  # 랜덤 지연
time.sleep(delay)

# 지수적 백오프 재시도
time.sleep(2 ** attempt_number)
```

#### 🔧 설정 가능한 API 관리
```python
from domain.stock.service.market_data_service import MarketDataService

service = MarketDataService()

# 보수적 모드 (높은 지연, 안전)
service.set_yahoo_settings(delay=2.0, retry_count=3, prefer_fred=True)

# 균형 모드 (표준 설정)
service.set_yahoo_settings(delay=1.0, retry_count=3, prefer_fred=True)

# 빠른 모드 (낮은 지연, 주의 필요)
service.set_yahoo_settings(delay=0.5, retry_count=2, prefer_fred=True)

# Yahoo 우선 모드 (FRED 장애 시)
service.set_yahoo_settings(delay=1.5, retry_count=2, prefer_fred=False)
```

#### 📊 API 사용 모니터링
```python
# 데이터 소스별 사용 통계 확인
stats = service.get_data_source_stats()
print(stats)
# 출력 예시:
# {
#     'fred_buffett': 8,    # Fed Z.1 버핏 지수 데이터
#     'yahoo_buffett': 2,   # Yahoo 백업 버핏 지수 데이터  
#     'fred_vix': 5,        # FRED VIX 데이터
#     'yahoo_vix': 1,       # Yahoo 백업 VIX 데이터
#     'fred_treasury': 3    # FRED 국채 수익률 데이터
# }
```

### 🚀 시장 데이터 수집 사용법

#### 기본 사용법
```python
from domain.stock.service.market_data_service import MarketDataService

# 서비스 초기화
service = MarketDataService()

# 모든 지표 업데이트 (FRED 우선, Yahoo 백업)
results = service.update_all_indicators()
print(f"업데이트 결과: {results}")
# {'buffett_indicator': True, 'vix': True, 'treasury_yield': True}

# 개별 지표 업데이트
service.update_buffett_indicator()  # Fed Z.1 → Yahoo ^W5000 백업
service.update_vix()               # FRED VIXCLS → Yahoo ^VIX 백업  
service.update_treasury_yield()   # FRED DGS10만 사용

# 최신 지표 값 조회
buffett = service.get_latest_buffett_indicator()  # 197.5
vix = service.get_latest_vix()                   # 20.38
print(f"버핏 지수: {buffett}%, VIX: {vix}")
```

#### 배치 작업 통합
```python
# 일일 배치 작업에서 자동 실행
python test_market_data_job.py

# 수동 실행 (테스트/개발용)
from infrastructure.scheduler.jobs.market_data_update_job import MarketDataUpdateJob

job = MarketDataUpdateJob()
job.execute()  # 모든 시장 지표 업데이트
```

#### 고급 설정 및 모니터링
```python
# API 제한 상황 대응 설정
service.set_yahoo_settings(
    delay=1.5,           # 1.5초 지연 (API 제한 안전)
    retry_count=3,       # 3회 재시도
    prefer_fred=True     # FRED 우선 사용
)

# 데이터 소스 혼합 사용 모니터링
stats = service.get_data_source_stats()
fed_usage = stats['fred_buffett'] + stats['fred_vix'] + stats['fred_treasury']
yahoo_usage = stats['yahoo_buffett'] + stats['yahoo_vix']

print(f"FRED 사용: {fed_usage}건, Yahoo 백업: {yahoo_usage}건")
print(f"백업 사용률: {yahoo_usage/(fed_usage+yahoo_usage)*100:.1f}%")
```

### 💡 Yahoo Finance 통합의 핵심 장점

1. **무중단 서비스**: FRED 장애 시에도 데이터 수집 지속
2. **API 제한 회피**: 지능적 지연 및 재시도로 429 Error 방지  
3. **데이터 품질 보장**: Fed Z.1과 Yahoo ^W5000 교차 검증
4. **유연한 설정**: 환경별 최적화된 API 호출 정책
5. **완전 자동화**: 사용자 개입 없이 백업 시스템 작동
6. **성능 모니터링**: 실시간 데이터 소스 사용 현황 추적

### 🔍 시장 데이터 검증

#### Fed Z.1 vs Yahoo ^W5000 비교
```bash
# 데이터 소스별 버핏 지수 계산 비교
Fed Z.1 기준:    197.5% (공식 데이터)
Yahoo ^W5000:    214.8% (실시간 추정)
차이:           17.3%p (변환 계수 조정으로 개선 가능)
```

#### 데이터 정확성 보장
- **Fed Z.1**: 분기별 공식 발표, 최고 신뢰도
- **Yahoo ^W5000**: 실시간 업데이트, 실용성 높음
- **교차 검증**: 두 소스 간 편차 모니터링으로 이상 데이터 감지

## 🤖 배치 잡 시스템

시스템은 5개의 주요 배치 잡을 통해 자동으로 운영됩니다:

### 1. 실시간 신호 감지 잡 (realtime_signal_detection_job.py)
- **실행 주기**: 시장 시간 중 매시간 (9시-16시)
- **주요 기능**:
  - 동적 전략 시스템 통합 (SignalDetectionService)
  - 다중 시간대 분석 (일봉 + 시간봉)
  - 지표 프리컴퓨팅 및 캐싱
  - 피보나치 레벨 계산
  - 시장 추세 분석
  - 실시간 매수/매도 신호 생성
- **데이터 처리**:
  - 일봉 데이터: 피보나치, 장기 추세 분석
  - 시간봉 데이터: 실시간 신호 감지
  - 기술적 지표: SMA, MACD, RSI, 스토캐스틱, ADX, 거래량
- **특징**:
  - 글로벌 캐시 시스템으로 성능 최적화
  - 레거시 시스템과 호환성 유지
  - 복합 감지기 지원

### 2. 시간별 OHLCV 업데이트 잡 (hourly_ohlcv_update_job.py)
- **실행 주기**: 매시간
- **주요 기능**:
  - Yahoo Finance에서 최신 시간봉 데이터 수집
  - 누락된 데이터 보완
  - 데이터 품질 검증
  - 실시간 가격 정보 업데이트
- **처리 범위**: 최근 7일간의 시간봉 데이터

### 3. 일별 OHLCV 업데이트 잡 (daily_ohlcv_update_job.py)
- **실행 주기**: 매일 오후 5시 (장 마감 후)
- **주요 기능**:
  - 일봉 데이터 업데이트
  - 장기 차트 데이터 관리
  - 월말/분기말 데이터 정합성 검증
- **처리 범위**: 최근 30일간의 일봉 데이터

### 4. 시장 데이터 업데이트 잡 (market_data_update_job.py) 🆕
- **실행 주기**: 매일 오후 6시 (장 마감 후)
- **주요 기능**:
  - **Buffett Indicator 업데이트**: Fed Z.1 → Yahoo ^W5000 백업
  - **VIX 업데이트**: FRED VIXCLS → Yahoo ^VIX 백업
  - **10년 국채 수익률 업데이트**: FRED DGS10
  - **API 호출 제한 관리**: 지능적 지연 및 재시도
  - **데이터 소스 모니터링**: 백업 시스템 사용률 추적
- **특징**:
  - Yahoo Finance API 제한 대응 (1초 지연, 3회 재시도)
  - 이중 데이터 소스로 무중단 서비스 보장
  - 실시간 데이터 품질 검증
  - 자동 백업 시스템 전환

### 5. 종목 메타데이터 업데이트 잡 (update_stock_metadata_job.py)
- **실행 주기**: 매일 오전 6시 (장 시작 전)
- **주요 기능**:
  - 종목 기본 정보 업데이트
  - 상장/폐지 종목 관리
  - 종목명, 섹터 정보 동기화
  - 분석 대상 종목 목록 관리

### 배치 잡 모니터링
```python
# 배치 잡 상태 확인
from infrastructure.scheduler.scheduler_manager import SchedulerManager

scheduler = SchedulerManager()
job_status = scheduler.get_job_status()
print(f"활성 잡 수: {job_status['active_jobs']}")
print(f"다음 실행 예정: {job_status['next_execution']}")

# 개별 잡 실행
python test_realtime_job.py      # 실시간 신호 감지 테스트
python test_hourly_ohlcv_job.py  # 시간별 데이터 업데이트 테스트
python test_daily_ohlcv_job.py   # 일별 데이터 업데이트 테스트
python test_market_data_job.py   # 시장 데이터 업데이트 테스트 🆕
```

### 배치 잡 설정
```python
# infrastructure/scheduler/settings.py
SCHEDULER_SETTINGS = {
    'realtime_signal_detection': {
        'hour': '9-16',           # 시장 시간
        'minute': '0',            # 매시 정각
        'timezone': 'US/Eastern'
    },
    'hourly_ohlcv_update': {
        'minute': '5',            # 매시 5분
        'timezone': 'US/Eastern'
    },
    'daily_ohlcv_update': {
        'hour': '17',             # 오후 5시
        'minute': '0',
        'timezone': 'US/Eastern'
    },
    'market_data_update': {       # 🆕 시장 데이터 업데이트
        'hour': '18',             # 오후 6시 (장 마감 후)
        'minute': '0',
        'timezone': 'US/Eastern'
    },
    'stock_metadata_update': {
        'hour': '6',              # 오전 6시
        'minute': '0',
        'timezone': 'US/Eastern'
    }
}
```

## 🏗️ 아키텍처

### 핵심 컴포넌트
- **StrategyManager**: 전략 관리 및 교체
- **BaseStrategy**: 전략 추상화 기반 클래스
- **StrategyFactory**: 전략 인스턴스 생성
- **SignalDetectionService**: 통합 신호 감지 서비스
- **CompositeDetectorManager**: 복합 감지기 관리 및 설정
- **SchedulerManager**: 배치 잡 스케줄링 및 관리
- **MarketDataService**: 시장 데이터 수집 및 관리 🆕
- **SQLMarketDataRepository**: 시장 데이터 저장소 🆕

### 호환성
- 기존 `DetectorFactory` 및 `SignalDetectionService`와 완전 호환
- 레거시 코드 수정 없이 새로운 시스템 활용 가능
- 점진적 마이그레이션 지원

### 🔥 주요 신규 기능 하이라이트

#### 📊 시장 데이터 시스템 (NEW!)
- **Buffett Indicator**: Fed Z.1 + Yahoo ^W5000 이중 소스
- **VIX 지수**: FRED + Yahoo 백업 시스템
- **Yahoo API 관리**: 호출 제한 대응 자동화
- **무중단 서비스**: 백업 시스템으로 99.9% 가용성 보장

#### 🤖 지능형 배치 시스템 (Enhanced!)
- **5개 자동화 잡**: 실시간 신호 + 시장 데이터 수집
- **API 제한 관리**: Yahoo Finance 429 Error 제로
- **데이터 품질 보장**: 이중 소스 교차 검증
- **성능 모니터링**: 실시간 데이터 소스 사용률 추적

## 📈 성능 최적화

- **지표 캐싱**: 동일한 지표를 여러 번 계산하지 않음
- **병렬 처리**: 여러 전략을 동시에 실행 가능
- **메모리 효율성**: 필요한 데이터만 메모리에 보관
- **선택적 지표 계산**: 전략에 필요한 지표만 계산
- **글로벌 캐시**: 다중 시간대 데이터 캐싱으로 성능 향상

## 🔍 백테스팅

새로운 다중 전략 백테스팅 시스템이 완전히 통합되어 있어 모든 전략들의 성능을 검증할 수 있습니다.
자세한 내용은 `BACKTESTING_README.md` 파일을 참조하세요.

### 기본 백테스팅
```bash
# 기본 백테스팅 (기존 호환성)
python run_backtest.py --mode single --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 레거시 신호 감지 시스템 사용 (검증된 안정적 백테스팅)
python run_backtest.py --mode single --use-legacy --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 레거시 전략 비교 (보수적/기본/공격적 설정 비교)
python run_backtest.py --mode comparison --use-legacy --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01
```

### 특정 전략 백테스팅
```bash
# AGGRESSIVE 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# CONSERVATIVE 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy CONSERVATIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# MOMENTUM 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy MOMENTUM --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 🆕 거시지표 기반 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy MACRO_DRIVEN --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

### 거시지표 전략 전용 분석 🆕
```bash
# VIX와 버핏지수 기반 거시지표 전략 종합 분석
python run_backtest.py --mode macro-analysis --tickers AAPL MSFT GOOGL --start-date 2024-01-01 --end-date 2025-01-01

# 거시지표 전략만 단독 테스트
python run_backtest.py --mode strategy --strategy MACRO_DRIVEN --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01
```

### 전략 비교 백테스팅
```bash
# 모든 주요 전략 비교 (거시지표 전략 포함)
python run_backtest.py --mode strategy-comparison --tickers AAPL MSFT GOOGL --start-date 2024-01-01 --end-date 2025-01-01

# 특정 전략들만 비교 (거시지표 전략 포함)
python run_backtest.py --mode strategy-comparison --compare-strategies CONSERVATIVE BALANCED AGGRESSIVE MACRO_DRIVEN --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01
```

### 전략 조합 백테스팅
```bash
# 균형잡힌 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01

# 보수적 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix conservative_mix --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 공격적 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix aggressive_mix --tickers NVDA TSLA --start-date 2024-01-01 --end-date 2025-01-01
```

### 자동 전략 선택 백테스팅
```bash
# 시장 상황에 따른 자동 전략 선택
python run_backtest.py --mode auto-strategy --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

### 고급 백테스팅 옵션
```bash
# 매개변수 최적화
python run_backtest.py --mode optimization --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 워크 포워드 분석
python run_backtest.py --mode walk-forward --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01

# 커스텀 설정으로 백테스팅
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01 --initial-capital 50000 --commission-rate 0.002 --risk-per-trade 0.03 --data-interval 1h
```

### 백테스팅 데모
전체 백테스팅 기능들을 체험해볼 수 있는 데모:
```bash
python strategy_backtest_demo.py
```

### 백테스팅 결과 분석
백테스팅 결과는 자동으로 `./backtest_results/` 디렉토리에 저장되며, 다음과 같은 정보를 포함합니다:
- 총 수익률 및 연환산 수익률
- 샤프 비율 및 최대 낙폭
- 승률 및 수익 팩터
- 전략별 성과 비교
- 상세 거래 로그

---

## 설치 및 설정

### 요구사항
```bash
pip install -r requirements.txt
```

### 데이터베이스 설정
SQLite 데이터베이스가 자동으로 생성됩니다.

### 환경 변수
필요한 API 키나 설정을 환경 변수로 설정하세요.

### 시스템 시작
```bash
# 전체 시스템 시작 (배치 잡 포함)
python main.py

# 배치 잡만 시작
python -m infrastructure.scheduler.scheduler_manager
```

---

## 🤝 기여하기

새로운 전략을 추가하거나 기존 전략을 개선하려면:

1. `domain/analysis/strategy/strategy_implementations.py`에 새 전략 클래스 추가
2. `domain/analysis/config/strategy_settings.py`에 전략 설정 추가
3. 테스트 및 검증

새로운 배치 잡을 추가하려면:

1. `infrastructure/scheduler/jobs/`에 새 잡 파일 추가
2. `infrastructure/scheduler/scheduler_manager.py`에 스케줄 등록
3. 테스트 스크립트 작성

---

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 등록해주세요. 