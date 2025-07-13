# Trend Pullback Strategy (추세추종 눌림목 전략)

## 전략 개요
- **목적**: 상승 추세 중 일시적 하락(눌림목) 구간에서 매수 기회를 포착하는 추세추종 전략
- **핵심 아이디어**: 장기/단기 추세가 일치하는 구간에서 SMA, ADX, RSI 신호를 조합하여 눌림목 매수 신호를 생성

## 구조 및 경로
- 메인 클래스: `domain/strategies/trend_pullback/trend_pullback_strategy.py`
- 커스텀 Detector:
  - `detectors/trend_pullback_sma_detector.py` (SMA)
  - `detectors/trend_pullback_adx_detector.py` (ADX)
  - `detectors/trend_pullback_rsi_detector.py` (RSI)
- 파라미터/가중치 config: `configs/trend_pullback_config.py`

## 주요 Detector 및 신호 산출 방식
- **TrendPullbackSMADetector**: SMA(5, 20) 골든/데드크로스, 추세 일치 등
- **TrendPullbackADXDetector**: ADX(14) 강도에 따라 추세 신호 점수 산출
- **TrendPullbackRSIDetector**: RSI(14) 과매수/과매도, 기준선 돌파 등
- 각 Detector는 공통 SignalDetector를 상속하며, 필요시 파라미터/로직 오버라이드 가능

## Config 분리 예시
```python
# domain/strategies/trend_pullback/configs/trend_pullback_config.py
SMA_WEIGHT = 5.0
ADX_WEIGHT = 4.0
RSI_WEIGHT = 6.0
# (추후 period 등 파라미터도 확장 가능)
```

## 전략 클래스 주요 메서드
- `initialize()`: 커스텀 Detector를 config에서 불러온 가중치로 초기화
- `analyze()`:
  - 입력: 인디케이터 포함 DataFrame, ticker, 시장/장기 추세 등
  - Detector 조합 신호 산출 및 점수 조정(추세 일치/불일치 가중치)
  - 신호 발생 시 TradingSignal 생성
  - **상세 로그**: 분석 시작/결과, 점수, 신호 근거 등 info/debug 레벨로 출력

## 로그 및 백테스팅 활용
- 분석 시작/결과, 점수, 신호 발생 여부, buy/sell score, signal details 등 핵심 정보가 로그로 남음
- 예시:
```
[TrendPullback] 분석 시작 | ticker=005930 | market_trend=UP | long_term_trend=UP
[TrendPullback] 시장/장기 추세 일치: score 1.1배 적용
[TrendPullback] 분석결과 | ticker=005930 | has_signal=True | score=8.25 | buy_score=8.25 | sell_score=0.00 | signal_details=[...]
```
- 백테스팅/실시간 분석 시 전략 동작 및 신호 근거 추적에 용이

## 팩토리/설정 연동
- `strategy_factory.py`, `static_strategies.py` 등에서 implementation_class 경로: 
  - `domain.strategies.trend_pullback.trend_pullback_strategy.TrendPullbackStrategy`
- 모든 참조 경로가 독립 패키지 구조로 일원화됨

## 유지보수/확장 포인트
- Detector별 파라미터, 가중치, 신호 로직을 config/클래스에서 쉽게 확장 가능
- 로그 기반 디버깅 및 백테스트 결과 해석이 용이 