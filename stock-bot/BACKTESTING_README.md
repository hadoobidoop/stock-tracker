# 백테스팅 시스템

이 백테스팅 시스템은 기존의 신호 감지 전략을 완전히 재현하여 과거 데이터로 전략의 성과를 평가합니다.

## 주요 특징

### ✅ 완전한 전략 재현
- **모든 매수매도 전략이 빠짐없이 포함됨**
- SMA/MACD 골든/데드 크로스
- RSI/스토캐스틱 과매수/과매도 신호
- 거래량 급증 확인
- ADX 강한 추세 감지
- 복합 신호 (MACD+거래량, RSI+스토캐스틱)
- 피보나치 레벨 지지/저항

### 📊 리스크 관리
- ATR 기반 손절매/익절매
- 포지션 크기 자동 계산 (리스크 기반)
- 최대 낙폭 모니터링
- 수수료 고려
- 동적 보유 기간 관리 (최대 보유 기간 제한 없음)

### 📈 성과 분석
- 승률, 수익팩터, 샤프비율
- 신호 강도별 성과 분석
- 시장 상황별 성과 분석
- 보유 기간별 성과 분석
- 월별 성과 분석

## 사용 방법

`run_backtest.py` 스크립트를 사용하여 다양한 모드로 백테스팅을 실행할 수 있습니다.

### 특정 전략으로 백테스팅
```bash
python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

### 여러 전략 비교 분석
```bash
python run_backtest.py --mode strategy-comparison --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

### 전략 조합(믹스)으로 백테스팅
```bash
python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

### 자동 전략 선택 백테스팅
```bash
python run_backtest.py --mode auto-strategy --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

### 매개변수 최적화
```bash
python run_backtest.py --mode optimization --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

### 워크 포워드 분석
```bash
python run_backtest.py --mode walk-forward --tickers AAPL MSFT NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

## 명령행 옵션

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--tickers` | 백테스트할 종목 리스트 (필수) | - |
| `--start-date` | 시작 날짜 (YYYY-MM-DD, 필수) | - |
| `--end-date` | 종료 날짜 (YYYY-MM-DD, 필수) | - |
| `--initial-capital` | 초기 자본금 | 100000 |
| `--commission-rate` | 수수료율 | 0.001 (0.1%) |
| `--risk-per-trade` | 거래당 리스크 비율 | 0.02 (2%) |
| `--data-interval` | 데이터 간격 (`1h` 또는 `1d`) | `1h` |
| `--output-dir` | 결과 저장 디렉토리 | `./backtest_results` |
| `--mode` | 실행 모드. `single`, `strategy`, `strategy-mix`, `auto-strategy`, `strategy-comparison`, `optimization`, `walk-forward`, `comparison` 중 선택 | `single` |
| `--strategy` | `strategy` 모드에서 사용할 전략 | - |
| `--strategy-mix` | `strategy-mix` 모드에서 사용할 전략 조합 | - |
| `--compare-strategies` | `strategy-comparison` 모드에서 비교할 전략 목록 (지정하지 않으면 전체 비교) | - |
| `--use-legacy` | 레거시 신호 감지 시스템 사용 여부 | `False` |

## 백테스트 결과 예시

```
============================================================
백테스트 결과 요약
============================================================
기간: 2023-01-01 ~ 2024-01-01
초기 자본: $100,000.00
최종 자본: $125,430.50
총 수익률: 25.43%
연환산 수익률: 25.43%
최대 낙폭: 8.75%
샤프 비율: 1.85
총 거래 수: 45
승률: 62.2%
수익 팩터: 1.87
============================================================
```

## 구현된 매수매도 전략

### 1. 추세 추종 전략
- **SMA 골든/데드 크로스**: 5일선이 20일선을 상향/하향 돌파
- **MACD 크로스**: MACD가 신호선을 상향/하향 돌파
- **ADX 강한 추세**: ADX > 25일 때 +DI/-DI 방향 추종

### 2. 모멘텀 반전 전략
- **RSI 과매수/과매도**: RSI 30/70 구간 탈출
- **스토캐스틱 크로스**: %K가 %D를 상향/하향 돌파

### 3. 거래량 확인 전략
- **거래량 급증**: 현재 거래량 > 평균 거래량 × 1.2

### 4. 복합 신호 전략
- **MACD + 거래량**: 골든크로스와 거래량 급증 동시 발생
- **RSI + 스토캐스틱**: 과매도 탈출과 스토캐스틱 매수 동시 발생
- **Any_Momentum**: RSI 또는 스토캐스틱 신호 중 하나 발생
- **Multi_Confirm**: SMA와 MACD 신호 동시 발생

### 5. 지지/저항 전략
- **피보나치 레벨**: 23.6%, 38.2%, 50%, 61.8% 되돌림 지점

## 리스크 관리 시스템

### 손절매 (Stop Loss)
- ATR 기반 동적 손절가 설정
- 매수: 진입가 - (ATR × 2)
- 매도: 진입가 + (ATR × 2)

### 익절매 (Take Profit)
- 리워드:리스크 비율 2:1 적용
- 손절가와 진입가 차이의 2배 지점에 설정

### 포지션 크기 관리
- 각 거래에서 포트폴리오의 2% 리스크
- 손절가 기준 포지션 크기 자동 계산

### 보유 기간 관리
- 동적 보유 기간: 신호 유효성에 따라 결정
- 최대 보유 기간 제한 없음
- 청산 조건: 반대 신호 발생 또는 손절/익절 도달

## 출력 파일

### 백테스트 리포트 (JSON)
```json
{
  "executive_summary": {
    "backtest_period": "2023-01-01 to 2024-01-01",
    "total_return": "25.43%",
    "annualized_return": "25.43%",
    "max_drawdown": "8.75%",
    "sharpe_ratio": "1.85",
    "win_rate": "62.2%",
    "total_trades": 45
  },
  "detailed_metrics": { ... },
  "trade_analysis": {
    "signal_strength": { ... },
    "market_conditions": { ... },
    "holding_periods": { ... }
  }
}
```

### 거래 로그 (CSV)
- 각 거래의 상세 정보
- 진입/청산 시점, 가격, 수익률
- 신호 세부사항

## 고급 기능

### 1. 매개변수 최적화
- 수수료율, 리스크 비율, 데이터 간격 등 최적화
- 샤프 비율 기준 최적 매개변수 탐색

### 2. 워크 포워드 분석
- 시간 순서대로 학습/테스트 반복
- 과최적화 방지 및 실제 거래 환경 시뮬레이션

### 3. 전략 비교
- 보수적/기본/공격적 전략 동시 비교
- 각 전략의 성과 지표 비교 분석

## 개발자 가이드

### 새로운 전략 추가

1. `domain/analysis/detectors/` 하위에 새로운 detector 구현
2. `SignalDetector` 추상 클래스 상속
3. `detect_signals` 메서드 구현
4. `DetectorFactory`에 새로운 detector 등록

### 복합 감지기 추가

1. `domain/analysis/detectors/composite/` 하위에 새로운 복합 감지기 구현
2. `CompositeDetector` 추상 클래스 상속
3. `detect_signals` 메서드 구현
4. `strategy_settings.py`에 복합 감지기 설정 추가
5. 하위 감지기 목록 설정

### 새로운 성과 지표 추가

1. `BacktestResult` 클래스에 새로운 메트릭 추가
2. `calculate_metrics` 메서드에 계산 로직 구현
3. 리포트 생성에 새로운 지표 포함

## 주의사항

1. **데이터 품질**: Yahoo Finance 데이터의 한계 고려
2. **수수료**: 실제 브로커 수수료와 차이 가능
3. **슬리피지**: 시장 충격 미고려
4. **생존자 편향**: 상장폐지 종목 미포함
5. **과최적화**: 백테스트 결과가 미래 성과를 보장하지 않음

## 라이센스

이 프로젝트는 내부 사용을 위한 것입니다.

## 지원

문의사항이나 버그 리포트는 개발팀에 연락하세요. 