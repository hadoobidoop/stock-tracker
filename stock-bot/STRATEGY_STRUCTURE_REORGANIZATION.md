# 전략 구조 재조직화 (Strategy Structure Reorganization)

## 개요

기존 `domain/strategies/` 패키지가 너무 복잡하게 구성되어 있어, 전략을 3개의 명확한 패키지로 분리하여 구조를 개선했습니다.

## 새로운 구조

### 1. 단일전략 (Single Strategies)
**위치**: `domain/strategies/single_strategies/`

개별적으로 동작하는 독립적인 전략들입니다.

**포함된 전략들**:
- `conservative/` - 보수적 전략
- `balanced/` - 균형잡힌 전략  
- `aggressive/` - 공격적 전략
- `momentum/` - 모멘텀 전략
- `mean_reversion/` - 평균회귀 전략
- `scalping/` - 스캘핑 전략
- `swing/` - 스윙 전략
- `trend_following/` - 추세추종 전략
- `trend_pullback/` - 추세추종 눌림목 전략
- `volatility_breakout/` - 변동성 돌파 전략
- `multi_timeframe/` - 다중 시간대 전략

### 2. 전략 조합 (Strategy Mixes)
**위치**: `domain/strategies/strategy_mixes/`

여러 단일전략을 조합하여 더 안정적이고 신뢰도 높은 신호를 생성하는 전략들입니다.

**포함된 전략들**:
- `conservative_mix/` - 보수적 조합 전략
- `balanced_mix/` - 균형잡힌 조합 전략
- `aggressive_mix/` - 공격적 조합 전략

### 3. 동적전략 (Dynamic Strategies)
**위치**: `domain/strategies/dynamic_strategies/`

시장 상황에 따라 실시간으로 전략을 조정하는 동적 전략들입니다.

**포함된 전략들**:
- `dynamic_strategy_manager/` - 동적 전략 관리자 (DynamicCompositeStrategy, DynamicStrategyManager)
- `adaptive_momentum_hybrid/` - 적응형 모멘텀 하이브리드 전략
- `conservative_reversion_hybrid/` - 보수적 회귀 하이브리드 전략
- `market_regime_hybrid/` - 시장 체제 하이브리드 전략

## 주요 변경사항

### 1. 디렉토리 구조 변경
```
기존: domain/strategies/
├── conservative/
├── balanced/
├── aggressive/
├── momentum/
├── mean_reversion/
├── scalping/
├── swing/
├── trend_following/
├── trend_pullback/
├── volatility_breakout/
├── multi_timeframe/
├── conservative_mix/
├── balanced_mix/
├── aggressive_mix/
├── dynamic/
├── adaptive_momentum_hybrid/
├── conservative_reversion_hybrid/
└── market_regime_hybrid/

변경: domain/strategies/
├── single_strategies/
│   ├── conservative/
│   ├── balanced/
│   ├── aggressive/
│   ├── momentum/
│   ├── mean_reversion/
│   ├── scalping/
│   ├── swing/
│   ├── trend_following/
│   ├── trend_pullback/
│   ├── volatility_breakout/
│   └── multi_timeframe/
├── strategy_mixes/
│   ├── conservative_mix/
│   ├── balanced_mix/
│   └── aggressive_mix/
└── dynamic_strategies/
    ├── dynamic_strategy_manager/
    ├── adaptive_momentum_hybrid/
    ├── conservative_reversion_hybrid/
    └── market_regime_hybrid/
```

### 2. Import 경로 업데이트
모든 import 경로를 새로운 구조에 맞게 업데이트했습니다:

**기존**:
```python
from domain.strategies.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.dynamic.dynamic_strategy import DynamicCompositeStrategy
from domain.strategies.conservative_mix.conservative_mix_strategy import ConservativeMixStrategy
```

**변경**:
```python
from domain.strategies.single_strategies.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.dynamic_strategy import DynamicCompositeStrategy
from domain.strategies.strategy_mixes.conservative_mix.conservative_mix_strategy import ConservativeMixStrategy
```

### 3. 패키지 __init__.py 파일 생성
각 패키지에 적절한 `__init__.py` 파일을 생성하여 import를 체계적으로 관리합니다.

## 장점

1. **명확한 분류**: 전략의 성격에 따라 명확하게 분류되어 찾기 쉽습니다.
2. **확장성**: 새로운 전략 추가 시 적절한 패키지에 배치할 수 있습니다.
3. **유지보수성**: 관련된 전략들이 함께 그룹화되어 관리가 용이합니다.
4. **의존성 관리**: 각 패키지별로 의존성을 명확히 관리할 수 있습니다.

## 사용법

### Import 예시
```python
# 단일전략 import
from domain.strategies.single_strategies.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.single_strategies.aggressive.aggressive_strategy import AggressiveStrategy

# 전략 조합 import
from domain.strategies.strategy_mixes.conservative_mix.conservative_mix_strategy import ConservativeMixStrategy

# 동적전략 import
from domain.strategies.dynamic_strategies.dynamic_strategy_manager.dynamic_strategy import DynamicCompositeStrategy
```

### 패키지별 import
```python
# 전체 패키지 import
from domain.strategies import single_strategies, strategy_mixes, dynamic_strategies

# 특정 패키지의 모든 전략 import
from domain.strategies.single_strategies import conservative, balanced, aggressive
from domain.strategies.strategy_mixes import conservative_mix, balanced_mix, aggressive_mix
from domain.strategies.dynamic_strategies import dynamic_strategy_manager, adaptive_momentum_hybrid
```

## 마이그레이션 완료

- ✅ 모든 전략 디렉토리 이동 완료
- ✅ Import 경로 업데이트 완료
- ✅ 패키지 __init__.py 파일 생성 완료
- ✅ 주요 시스템 파일들의 import 경로 수정 완료
- ✅ 테스트 및 검증 완료

## 주의사항

1. **기존 코드 호환성**: 모든 import 경로가 업데이트되었으므로 기존 코드에서 전략을 import할 때는 새로운 경로를 사용해야 합니다.
2. **문서 업데이트**: README.md 등 관련 문서가 새로운 구조에 맞게 업데이트되었습니다.
3. **테스트**: 모든 import가 정상적으로 동작하는지 확인되었습니다. 