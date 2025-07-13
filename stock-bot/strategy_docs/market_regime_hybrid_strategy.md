# Market Regime Hybrid Strategy (시장 체제 적응 하이브리드)

## 전략 개요
- **목적**: 시장의 추세(market_trend)와 변동성(VIX)을 진단하여, 상황에 따라 하위 전략(추세추종, 평균회귀, 변동성돌파) 중 하나를 동적으로 선택해 신호를 생성하는 하이브리드 전략
- **핵심 아이디어**: 시장 체제(Trending, Volatile Trending, Mean Reversion, Sideways)에 따라 최적의 전략을 자동 선택

## 구조 및 경로
- 메인 클래스: `domain/strategies/market_regime_hybrid/market_regime_hybrid_strategy.py`
- 하위 전략 직접 참조:
  - `trend_following/trend_following_strategy.py`
  - `mean_reversion/mean_reversion_strategy.py`
  - `volatility_breakout/volatility_breakout_strategy.py`
- 파라미터/가중치 config: `configs/market_regime_hybrid_config.py`

## 주요 동작 및 신호 산출 방식
- **시장 체제 진단**: market_trend, VIX 값으로 시장 상황 분류
- **하위 전략 선택**:
  - Trending: 추세추종 전략
  - Volatile Trending: 변동성돌파 전략
  - Mean Reversion: 평균회귀 전략
  - Sideways: 신호 없음
- **점수 조정**:
  - VIX 임계값에 따라 buy/sell 점수 동적 조정
  - 장기추세(BULLISH/BEARISH) 가중치 적용
- **신호 근거**: 선택된 하위 전략명, 세부 신호 근거 등 기록

## Config 분리 예시
```python
# domain/strategies/market_regime_hybrid/configs/market_regime_hybrid_config.py
VIX_VOLATILE_THRESHOLD = 25
VIX_HIGH_RISK_THRESHOLD = 30
VIX_LOW_RISK_THRESHOLD = 15
VIX_HIGH_RISK_MULTIPLIER = 0.7
VIX_LOW_RISK_MULTIPLIER = 1.2
BULLISH_BONUS = 1.2
BEARISH_BONUS = 1.2
```

## 전략 클래스 주요 메서드
- `initialize()`: 모든 하위 전략을 초기화
- `analyze()`:
  - 입력: 인디케이터 포함 DataFrame, ticker, 시장/장기 추세 등
  - 시장 체제 진단 → 하위 전략 선택 → 하위 전략 analyze() 실행 → 점수/신호 근거 조정
  - **상세 로그**: 분석 시작/결과, regime, VIX, 점수, 신호 근거 등 info/debug 레벨로 출력

## 로그 및 백테스팅 활용
- 분석 시작/결과, regime, VIX, 신호 발생 여부, buy/sell score, signal details 등 핵심 정보가 로그로 남음
- 예시:
```
[MarketRegimeHybrid] 분석 시작 | ticker=005930 | market_trend=UP | long_term_trend=UP | VIX=18.2
[2024-07-10] Market Regime for 005930: Trending (VIX: 18.20) -> Chosen Strategy: TrendFollowingStrategy
[MarketRegimeHybrid] 결과 | ticker=005930 | regime=Trending | vix=18.20 | has_signal=True | buy_score=7.80 | sell_score=0.00 | signal_details=[...]
```
- 백테스팅/실시간 분석 시 전략 동작 및 신호 근거 추적에 용이

## 팩토리/설정 연동
- `strategy_factory.py`, `static_strategies.py` 등에서 implementation_class 경로: 
  - `domain.strategies.market_regime_hybrid.market_regime_hybrid_strategy.MarketRegimeHybridStrategy`
- 모든 참조 경로가 독립 패키지 구조로 일원화됨

## 유지보수/확장 포인트
- 하위 전략 직접 참조로 의존성 명확화, config 분리로 파라미터 관리 용이
- 로그 기반 디버깅 및 백테스트 결과 해석이 용이
- 하위 전략/시장 체제/점수 조정 로직 등 확장/튜닝이 쉬움 