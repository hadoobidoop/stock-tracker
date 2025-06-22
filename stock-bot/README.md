# Stock Analyzer Bot 📈

주식 기술적 분석 및 자동 신호 감지를 위한 고급 전략 시스템

## 🎯 새로운 전략 시스템 특징

### Multi-Strategy Support
- **동적 전략 교체**: 런타임에 전략을 바꿀 수 있는 "Hot-swapping" 지원
- **전략 조합**: 여러 전략을 조합하여 앙상블 방식으로 분석
- **자동 전략 선택**: 시장 상황에 따라 최적 전략 자동 선택
- **지표 프리컴퓨팅**: 모든 기술적 지표를 미리 계산하여 성능 최적화

### 8가지 전략 타입
1. **CONSERVATIVE** - 보수적 투자 전략
2. **BALANCED** - 균형잡힌 기본 전략
3. **AGGRESSIVE** - 공격적 고수익 추구 전략
4. **MOMENTUM** - 모멘텀 기반 전략
5. **TREND_FOLLOWING** - 추세 추종 전략
6. **CONTRARIAN** - 역투자 전략
7. **SCALPING** - 단기 스캘핑 전략
8. **SWING** - 스윙 트레이딩 전략

### 전략 조합 모드
- **SINGLE**: 단일 전략 사용
- **WEIGHTED**: 가중 평균 조합
- **VOTING**: 투표 방식 조합
- **ENSEMBLE**: 앙상블 방식 조합

## 🚀 사용법

### 기본 실행
```bash
# 기본 balanced 전략으로 실행
python main.py

# 특정 전략으로 실행
python main.py --strategy conservative
python main.py --strategy aggressive
python main.py --strategy momentum
```

### 전략 조합 사용
```bash
# 균형잡힌 조합 전략
python main.py --strategy-mix balanced_mix

# 보수적 조합 전략
python main.py --strategy-mix conservative_mix

# 공격적 조합 전략
python main.py --strategy-mix aggressive_mix
```

### 자동 전략 선택
```bash
# 시장 상황에 따른 자동 전략 선택
python main.py --auto-strategy
```

### 전략 설정 관리
```bash
# 사용 가능한 전략 목록 보기
python main.py --list-strategies

# 전략 설정 파일에서 로드
python main.py --load-strategies ./strategy_configs/my_config.json
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

### 프로그래밍 방식 사용

```python
from domain.analysis.service.signal_detection_service import EnhancedSignalDetectionService
from domain.analysis.config.strategy_settings import StrategyType

# 서비스 초기화
service = EnhancedSignalDetectionService()
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

## 🏗️ 아키텍처

### 핵심 컴포넌트
- **StrategyManager**: 전략 관리 및 교체
- **BaseStrategy**: 전략 추상화 기반 클래스
- **StrategyFactory**: 전략 인스턴스 생성
- **EnhancedSignalDetectionService**: 통합 신호 감지 서비스

### 호환성
- 기존 `DetectorFactory` 및 `SignalDetectionService`와 완전 호환
- 레거시 코드 수정 없이 새로운 시스템 활용 가능
- 점진적 마이그레이션 지원

## 📈 성능 최적화

- **지표 캐싱**: 동일한 지표를 여러 번 계산하지 않음
- **병렬 처리**: 여러 전략을 동시에 실행 가능
- **메모리 효율성**: 필요한 데이터만 메모리에 보관
- **선택적 지표 계산**: 전략에 필요한 지표만 계산

## 🔍 백테스팅

새로운 다중 전략 백테스팅 시스템이 완전히 통합되어 있어 모든 전략들의 성능을 검증할 수 있습니다.

### 기본 백테스팅
```bash
# 기본 백테스팅 (기존 호환성)
python run_backtest.py --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# 레거시 시스템 사용
python run_backtest.py --mode single --use-legacy --tickers AAPL --start-date 2023-01-01 --end-date 2024-01-01
```

### 특정 전략 백테스팅
```bash
# AGGRESSIVE 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# CONSERVATIVE 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy CONSERVATIVE --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# MOMENTUM 전략으로 백테스팅
python run_backtest.py --mode strategy --strategy MOMENTUM --tickers AAPL NVDA --start-date 2023-01-01 --end-date 2024-01-01
```

### 전략 비교 백테스팅
```bash
# 모든 주요 전략 비교
python run_backtest.py --mode strategy-comparison --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# 특정 전략들만 비교
python run_backtest.py --mode strategy-comparison --compare-strategies CONSERVATIVE BALANCED AGGRESSIVE --tickers AAPL --start-date 2023-01-01 --end-date 2024-01-01
```

### 전략 조합 백테스팅
```bash
# 균형잡힌 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix --tickers AAPL --start-date 2023-01-01 --end-date 2024-01-01

# 보수적 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix conservative_mix --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# 공격적 전략 조합
python run_backtest.py --mode strategy-mix --strategy-mix aggressive_mix --tickers NVDA TSLA --start-date 2023-01-01 --end-date 2024-01-01
```

### 자동 전략 선택 백테스팅
```bash
# 시장 상황에 따른 자동 전략 선택
python run_backtest.py --mode auto-strategy --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01
```

### 고급 백테스팅 옵션
```bash
# 매개변수 최적화
python run_backtest.py --mode optimization --tickers AAPL --start-date 2023-01-01 --end-date 2024-01-01

# 워크 포워드 분석
python run_backtest.py --mode walk-forward --tickers AAPL MSFT --start-date 2023-01-01 --end-date 2024-01-01

# 커스텀 설정
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL --start-date 2023-01-01 --end-date 2024-01-01 --initial-capital 50000 --commission-rate 0.002 --risk-per-trade 0.03
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

---

## 🤝 기여하기

새로운 전략을 추가하거나 기존 전략을 개선하려면:

1. `domain/analysis/strategy/strategy_implementations.py`에 새 전략 클래스 추가
2. `domain/analysis/config/strategy_settings.py`에 전략 설정 추가
3. 테스트 및 검증

---

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 등록해주세요. 