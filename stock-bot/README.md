# Stock Tracker Bot

실시간 주식 분석 및 신호 감지 시스템

## 개요

이 프로젝트는 Yahoo Finance API를 활용하여 실시간으로 주식 데이터를 분석하고, 다양한 기술적 지표를 기반으로 매수/매도 신호를 감지하는 자동화된 시스템입니다.

## 주요 기능

### 1. 실시간 신호 감지
- **시간봉 분석**: 1시간봉 데이터를 기반으로 실시간 신호 감지
- **다중 지표 분석**: RSI, MACD, 스토캐스틱, 볼린저 밴드 등 다양한 기술적 지표 활용
- **시장 추세 반영**: S&P 500 기준 전체 시장 추세를 신호에 반영
- **장기 추세 확인**: 50일 이동평균을 기준으로 한 장기 추세 분석

### 2. 기술적 지표 계산
- **이동평균선 (SMA)**: 5일, 20일, 60일 이동평균
- **RSI (Relative Strength Index)**: 14일 기준 과매수/과매도 판단
- **MACD**: 12, 26, 9 설정으로 추세 전환 감지
- **스토캐스틱**: %K, %D 크로스오버 신호
- **볼린저 밴드**: 20일, 2표준편차 설정
- **ATR (Average True Range)**: 변동성 측정
- **ADX (Average Directional Index)**: 추세 강도 측정

### 3. 스케줄링 시스템
- **자동 실행**: APScheduler를 사용한 자동화된 작업 실행
- **장 시간 감지**: 미국 동부 시간 기준 장 시간에만 실행
- **메타데이터 업데이트**: 주간 자동 메타데이터 업데이트

### 4. 데이터 관리
- **캐싱 시스템**: 일일 데이터 캐시로 API 호출 최적화
- **데이터베이스 저장**: SQLAlchemy를 사용한 지표 및 신호 데이터 저장
- **피보나치 레벨**: 지지/저항 레벨 계산

## 프로젝트 구조

```
stock-bot/
├── domain/                          # 도메인 로직
│   ├── analysis/                    # 분석 관련
│   │   ├── base/                    # 기본 클래스
│   │   ├── config/                  # 분석 설정
│   │   ├── detectors/               # 신호 감지기
│   │   ├── service/                 # 분석 서비스
│   │   └── utils/                   # 분석 유틸리티
│   ├── notification/                # 알림 시스템
│   └── stock/                       # 주식 관련
├── infrastructure/                  # 인프라스트럭처
│   ├── client/                      # 외부 API 클라이언트
│   ├── db/                          # 데이터베이스
│   ├── logging/                     # 로깅 시스템
│   └── scheduler/                   # 스케줄러
├── main.py                          # 메인 실행 파일
└── requirements.txt                 # 의존성 목록
```

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 설정
`.env` 파일을 생성하고 다음 설정을 추가하세요:
```env
DATABASE_URL=sqlite:///stock_bot.db
LOG_LEVEL=INFO
```

### 3. 실행
```bash
# 메인 애플리케이션 실행
python main.py

# 실시간 신호 감지 작업 테스트
python test_realtime_job.py
```

## 설정

### 분석할 주식 설정
`domain/stock/config/settings.py`에서 분석할 주식 목록을 설정할 수 있습니다:
```python
STOCK_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"
]
```

### 스케줄링 설정
`infrastructure/scheduler/settings.py`에서 작업 실행 시간을 조정할 수 있습니다:
```python
REALTIME_SIGNAL_JOB = {
    'id': 'realtime_signal_job',
    'name': 'Real-time Signal Detection (Hourly)',
    'cron': {
        'day_of_week': 'mon-fri',    # 월-금
        'hour': '9-16',              # 9시-16시
        'minute': '*'                 # 매분 실행
    }
}
```

## 신호 감지 시스템

### 신호 감지기 종류
1. **추세 추종 감지기**
   - SMA 골든/데드 크로스
   - MACD 크로스오버
   - ADX 강한 추세

2. **모멘텀 감지기**
   - RSI 과매수/과매도
   - 스토캐스틱 크로스

3. **거래량 감지기**
   - 거래량 급증 감지

4. **복합 감지기**
   - MACD + 거래량 확인
   - RSI + 스토캐스틱 동시 신호

### 신호 점수 시스템
- 각 감지기는 가중치를 가짐
- 시장 추세에 따라 점수 조정
- 임계값 이상의 점수에서 신호 발생

## 데이터베이스 스키마

### 주요 테이블
- `stock_metadata`: 주식 메타데이터
- `technical_indicators`: 기술적 지표 데이터
- `trading_signals`: 거래 신호 데이터
- `intraday_ohlcv`: 분봉 OHLCV 데이터

## 로깅

시스템은 상세한 로깅을 제공합니다:
- 작업 실행 상태
- 신호 감지 결과
- 오류 및 예외 상황
- 성능 메트릭

## 개발 가이드

### 새로운 신호 감지기 추가
1. `domain/analysis/detectors/` 하위에 새 감지기 클래스 생성
2. `SignalDetector` 추상 클래스 상속
3. `detect_signals` 메서드 구현
4. `DetectorFactory`에 등록

### 새로운 기술적 지표 추가
1. `domain/analysis/utils/technical_indicators.py`에 계산 함수 추가
2. `calculate_all_indicators` 함수에 통합
3. 데이터베이스 스키마 업데이트

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다. 