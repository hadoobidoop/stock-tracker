# 🚀 동적 가중치 조절 시스템 (Dynamic Weight Adjustment System)

## 📋 개요

기존의 정적 필터링 시스템을 진화시켜, **거시 경제 상황에 따라 기술적 지표의 가중치를 동적으로 변경하는 지능형 시스템**입니다.

### 🎯 핵심 특징

1. **🔄 동적 가중치 조절**: VIX, 공포탐욕지수, 금리 등 거시 지표에 따라 실시간으로 기술적 지표 가중치 조정
2. **🧠 지능형 의사결정**: DecisionContext를 통한 투명하고 추적 가능한 의사결정 과정
3. **🔧 모듈화된 규칙 엔진**: Modifier 시스템을 통한 유연하고 확장 가능한 규칙 관리
4. **🔗 완벽한 호환성**: 기존 정적 전략과 완전히 호환되는 설계

---

## 🏗️ 시스템 아키텍처

### 핵심 컴포넌트

```
📁 domain/analysis/
├── 📁 config/
│   └── 📄 strategy_configs.py      # 동적 전략 및 모디파이어 정의
├── 📁 strategy/
│   ├── 📄 decision_context.py      # 의사결정 컨텍스트 관리
│   ├── 📄 modifiers.py            # 모디파이어 시스템
│   ├── 📄 dynamic_strategy.py     # 동적 전략 구현
│   └── 📄 strategy_manager.py     # 전략 매니저 (확장됨)
└── 📄 dynamic_strategy_demo.py    # 데모 스크립트
```

### 데이터 흐름

```
거시 지표 데이터 → Modifier 엔진 → DecisionContext → 가중치 조정 → 최종 신호
       ↓              ↓              ↓              ↓           ↓
   [VIX, 금리,    [조건 확인,    [가중치, 점수,    [RSI ↑,      [BUY/SELL/
    달러지수...]    액션 적용]     임계값 관리]     MACD ↓...]    HOLD]
```

---

## 📚 주요 클래스 및 개념

### 1. DecisionContext
모든 의사결정 과정을 담는 핵심 컨텍스트 객체

```python
class DecisionContext:
    # 가중치 관리
    original_weights: Dict[str, float]    # 기본 가중치
    current_weights: Dict[str, float]     # 조정된 가중치
    weight_adjustments: List[WeightAdjustment]  # 조정 기록
    
    # 점수 관리
    detector_raw_scores: Dict[str, float]     # 원시 점수
    detector_weighted_scores: Dict[str, float]  # 가중 점수
    final_score: float                       # 최종 점수
    
    # 조정 요소
    current_threshold: float                 # 조정된 임계값
    score_multipliers: List[float]           # 점수 배율
    
    # 거부 상태
    is_vetoed: bool                         # 거부 여부
    veto_reason: str                        # 거부 사유
```

### 2. Modifier 시스템
거시 지표에 따른 규칙을 모듈화한 시스템

```python
# 모디파이어 정의 예시
"vix_high_volatility_mode": ModifierDefinition(
    description="VIX가 25를 넘으면 변동성 장세로 판단, RSI 가중치 증가",
    detector="vix",
    condition=ModifierCondition(operator=">", value=25),
    action=ModifierAction(
        type=ModifierActionType.ADJUST_WEIGHTS,
        adjustments={
            "rsi": 0.2,   # RSI 가중치 +0.2 증가
            "macd": -0.2  # MACD 가중치 -0.2 감소
        }
    ),
    priority=50
)
```

### 3. DynamicCompositeStrategy
동적 가중치 조절을 수행하는 전략 클래스

```python
class DynamicCompositeStrategy(BaseStrategy):
    def analyze(self, df_with_indicators, ticker, ...):
        # 1. DecisionContext 생성
        context = DecisionContext(self.strategy_config)
        
        # 2. 기술적 지표 점수 계산
        self._calculate_technical_scores(context, df)
        
        # 3. 모디파이어 적용
        self.modifier_engine.apply_all(context, df, market_data)
        
        # 4. 최종 점수 계산 및 신호 생성
        context.calculate_final_score()
        return self._create_strategy_result(context, ...)
```

---

## 🔧 설정 및 사용법

### 1. 전략 정의 (`strategy_configs.py`)

```python
STRATEGY_DEFINITIONS = {
    "dynamic_weight_strategy": {
        "description": "거시 상황에 따라 기술적 지표의 가중치가 동적으로 변하는 전략",
        "signal_threshold": 8.0,
        "risk_per_trade": 0.02,
        "detectors": {
            "rsi": {"weight": 0.3},
            "macd": {"weight": 0.3},
            "sma": {"weight": 0.2},
            "stoch": {"weight": 0.15},
            "adx": {"weight": 0.05}
        },
        "modifiers": [
            "extreme_fear_filter",
            "vix_high_volatility_mode",
            "market_in_uptrend",
            # ... 추가 모디파이어
        ]
    }
}
```

### 2. 모디파이어 정의

```python
MODIFIER_DEFINITIONS = {
    "market_in_uptrend": ModifierDefinition(
        description="S&P 500이 200일선 위에 있으면 추세 추종 지표 가중치 증가",
        detector="sp500_sma_200",
        condition=ModifierCondition(operator="is_above"),
        action=ModifierAction(
            type=ModifierActionType.ADJUST_WEIGHTS,
            adjustments={
                "macd": 0.15,
                "sma": 0.15,
                "adx": 0.1
            }
        ),
        priority=60
    )
}
```

### 3. 기본 사용법

```python
from domain.analysis.strategy.strategy_manager import StrategyManager

# 1. 전략 매니저 초기화
manager = StrategyManager()
manager.initialize_strategies()

# 2. 동적 전략으로 전환
manager.switch_to_dynamic_strategy("dynamic_weight_strategy")

# 3. 분석 실행
result = manager.analyze_with_current_strategy(
    df_with_indicators=price_data,
    ticker="AAPL",
    market_trend=TrendType.NEUTRAL,
    daily_extra_indicators={
        "VIX": 32.1,
        "FEAR_GREED_INDEX": 25,
        "DXY": 106.8,
        "US_10Y_TREASURY_YIELD": 4.8
    }
)

# 4. 결과 확인
print(f"신호: {result.signal_type}")
print(f"점수: {result.total_score}")
print(f"신뢰도: {result.confidence:.1%}")
```

---

## 🎛️ 모디파이어 액션 타입

| 액션 타입 | 설명 | 예시 |
|----------|------|------|
| `VETO_BUY` | 매수 신호 거부 | VIX > 30일 때 매수 중단 |
| `VETO_SELL` | 매도 신호 거부 | 극도 공포 상태에서 패닉셀링 방지 |
| `VETO_ALL` | 모든 거래 중단 | VIX > 35일 때 전체 거래 중단 |
| `ADJUST_WEIGHTS` | 가중치 조정 | 변동성 높을 때 RSI 비중 증가 |
| `ADJUST_SCORE` | 점수 배율 적용 | 탐욕 지수 높을 때 점수 20% 감소 |
| `ADJUST_THRESHOLD` | 임계값 조정 | 저변동성 환경에서 임계값 상향 |

---

## 📊 데모 실행

```bash
# 데모 스크립트 실행
python dynamic_strategy_demo.py
```

### 데모 내용
1. **전략 비교**: 정적 vs 동적 전략 성능 비교
2. **상세 로깅**: DecisionContext 의사결정 과정 추적
3. **모디파이어 시연**: 다양한 시장 상황에서의 모디파이어 작동

---

## 🔍 상세 분석 및 디버깅

### DecisionContext 로그 조회

```python
# 상세 의사결정 로그
logs = manager.get_dynamic_strategy_detailed_log()
for log in logs:
    print(f"[{log['timestamp']}] {log['step']}: {log['action']}")

# 컨텍스트 요약
summary = manager.get_dynamic_strategy_info()
print(f"최종 점수: {summary['last_analysis']['final_score']}")
print(f"가중치 변경: {summary['last_analysis']['weight_changes']}개")
```

### 모디파이어 적용 내역

```python
context = strategy.get_last_decision_context()
for modifier in context.modifier_applications:
    if modifier.applied:
        print(f"✅ {modifier.modifier_name}: {modifier.reason}")
```

---

## 🔮 확장 가능성

### 새로운 모디파이어 추가

```python
# 새로운 모디파이어 정의
"crypto_fear_greed": ModifierDefinition(
    description="비트코인 공포탐욕지수 기반 조정",
    detector="btc_fear_greed",
    condition=ModifierCondition(operator="<", value=20),
    action=ModifierAction(
        type=ModifierActionType.ADJUST_WEIGHTS,
        adjustments={"volume": 0.3}  # 거래량 지표 비중 증가
    )
)
```

### 커스텀 액션 타입

```python
class CustomModifierActionType(Enum):
    SEASONAL_ADJUSTMENT = "SEASONAL_ADJUSTMENT"  # 계절성 조정
    SECTOR_ROTATION = "SECTOR_ROTATION"          # 섹터 로테이션
    RISK_PARITY = "RISK_PARITY"                 # 리스크 패리티
```

---

## 📈 성능 최적화

### 캐싱 활용
- 거시 지표 데이터 캐싱
- DecisionContext 재사용
- 모디파이어 결과 메모이제이션

### 병렬 처리
- 여러 전략 동시 분석
- 모디파이어 병렬 적용
- 백테스팅 병렬화

---

## 🧪 테스트 및 검증

### 단위 테스트
```python
def test_vix_volatility_modifier():
    context = DecisionContext(strategy_config)
    market_data = {"vix": 30.0}
    
    modifier = ModifierFactory.create_modifier("vix_high_volatility_mode", definition)
    result = modifier.process(context, df, market_data)
    
    assert result == True
    assert context.current_weights["rsi"] > context.original_weights["rsi"]
```

### 백테스팅
```python
from run_backtest import BacktestingEngine

engine = BacktestingEngine()
results = engine.run_strategy_backtest(
    strategy_name="dynamic_weight_strategy",
    start_date="2023-01-01",
    end_date="2024-01-01",
    tickers=["AAPL", "MSFT", "GOOGL"]
)
```

---

## 🎯 마이그레이션 가이드

### 기존 시스템에서 마이그레이션

1. **기존 전략 유지**: 모든 기존 정적 전략은 그대로 동작
2. **점진적 도입**: 특정 종목이나 상황에서만 동적 전략 활용
3. **성능 모니터링**: A/B 테스트를 통한 성능 비교
4. **설정 이관**: 기존 필터 규칙을 모디파이어로 변환

### 호환성 체크리스트
- ✅ 기존 BaseStrategy 인터페이스 호환
- ✅ StrategyManager API 호환
- ✅ 백테스팅 시스템 호환
- ✅ 로깅 및 모니터링 시스템 호환

---

## 🚀 결론

동적 가중치 조절 시스템은 **정적 필터링의 한계를 극복**하고, **거시 경제 환경 변화에 능동적으로 대응**할 수 있는 차세대 거래 전략 시스템입니다.

### 주요 이점
- 📊 **적응성**: 시장 상황 변화에 실시간 대응
- 🔍 **투명성**: 모든 의사결정 과정 추적 가능
- 🔧 **확장성**: 새로운 규칙과 지표 쉽게 추가
- 🛡️ **안정성**: 기존 시스템과 완벽한 호환성

이제 **애널리스트의 모든 매매 아이디어가 명확한 '레시피' 형태로 체계화**되어, 시스템의 가장 중요한 **지적 자산**으로 축적됩니다! 🎉 