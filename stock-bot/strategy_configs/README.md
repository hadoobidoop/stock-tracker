# 전략 설정 관리 (Strategy Configuration Management)

이 디렉토리는 주식 거래 전략의 설정 파일들을 체계적으로 관리합니다.

## 📁 디렉토리 구조

```
strategy_configs/
├── README.md                     # 이 파일
├── index.json                    # 전략 인덱스 파일
├── config_loader.py              # 설정 로더 모듈
├── config_manager.py             # CLI 관리 도구
├── strategies/                   # 조직화된 전략 설정들
│   ├── basic/                    # 기본 전략들
│   │   ├── conservative_config.json
│   │   ├── balanced_config.json
│   │   └── aggressive_config.json
│   ├── momentum/                 # 모멘텀 기반 전략들
│   │   └── momentum_config.json
│   ├── trend/                    # 추세 기반 전략들
│   │   ├── trend_following_config.json
│   │   └── trend_pullback_config.json
│   ├── reversion/                # 평균 회귀 전략들
│   │   └── mean_reversion_config.json
│   └── advanced/                 # 고급/하이브리드 전략들
│       ├── scalping_config.json
│       ├── volatility_breakout_config.json
│       └── market_regime_hybrid_config.json
└── archived/                     # 기존 대용량 설정 파일들
    ├── startup_config_20250719_004016.json
    ├── startup_config_20250719_105814.json
    ├── startup_config_20250719_110025.json
    └── startup_config_20250719_110326.json
```

## 🎯 전략 카테고리

### Basic Strategies (기본 전략)
- **Conservative**: 보수적 위험 관리, 높은 신뢰도 신호만 사용
- **Balanced**: 균형잡힌 위험/수익 비율
- **Aggressive**: 공격적 거래, 더 많은 기회 포착

### Momentum Strategies (모멘텀 전략)
- **Momentum**: RSI, Stochastic 등 모멘텀 지표 중심

### Trend Strategies (추세 전략)
- **Trend Following**: SMA, MACD, ADX 등 추세 추종
- **Trend Pullback**: 추세 중 눌림목 매수

### Reversion Strategies (평균 회귀 전략)
- **Mean Reversion**: Bollinger Bands, RSI 기반 평균 회귀

### Advanced Strategies (고급 전략)
- **Scalping**: 초단기 거래 전략
- **Volatility Breakout**: 변동성 돌파 감지
- **Market Regime Hybrid**: 시장 상황 적응 하이브리드

## 🛠️ 사용법

### CLI 관리 도구

```bash
# 모든 전략 나열
python config_manager.py list

# 특정 전략 상세 정보
python config_manager.py show conservative

# 설정 구조 유효성 검사
python config_manager.py validate

# 레거시 설정 마이그레이션
python config_manager.py migrate old_config.json --output-dir ./new_configs
```

### 프로그래밍에서 사용

```python
from strategy_configs.config_loader import load_strategy_config, load_all_strategies

# 개별 전략 로드
conservative_config = load_strategy_config('conservative')

# 모든 전략 로드
all_configs = load_all_strategies()

# 특정 카테고리 전략들만 로드
from strategy_configs.config_loader import get_strategy_config_loader
loader = get_strategy_config_loader()
basic_strategies = ['conservative', 'balanced', 'aggressive']
basic_configs = loader.load_multiple_strategies(basic_strategies)
```

### 메인 애플리케이션에서 로드

```bash
# 새로운 조직화된 구조에서 로드
python main.py --load-strategies strategy_configs/index.json

# 기존 레거시 파일에서 로드 (아카이브)
python main.py --load-strategies strategy_configs/archived/startup_config_20250719_110326.json
```

## 📋 설정 파일 형식

각 개별 전략 설정 파일은 다음 구조를 가집니다:

```json
{
  "name": "전략 이름",
  "description": "전략 설명",
  "signal_threshold": 8.0,
  "risk_per_trade": 0.02,
  "implementation_class": "구현 클래스 경로",
  "strategy_type": "StrategyType.BALANCED",
  "max_positions": 4,
  "position_hold_hours": 72,
  "stop_loss_percentage": 5.0,
  "take_profit_percentage": 12.0,
  "score_multiplier": 1.0,
  "long_term_bullish_multiplier": 1.2,
  "long_term_bearish_multiplier": 1.2,
  "detector_weights": {
    "sma": 5.0,
    "macd": 5.0,
    "rsi": 3.0,
    "volume": 4.0,
    "adx": 4.0,
    "composite": 7.0
  },
  "detectors": [],
  "market_filters": {},
  "position_management": {},
  "metadata": {
    "created_at": "2025-07-19T11:03:26Z",
    "source_file": "startup_config_20250719_110326.json",
    "category": "basic"
  }
}
```

## 🔧 설정 추가/수정

### 새 전략 추가

1. 적절한 카테고리 디렉토리에 `{strategy_name}_config.json` 파일 생성
2. 위의 형식에 맞춰 설정 작성
3. `index.json` 파일 업데이트 (선택사항, 자동 스캔됨)
4. `python config_manager.py validate`로 유효성 검사

### 기존 전략 수정

1. 해당 전략의 JSON 파일 직접 편집
2. 유효성 검사 실행
3. 애플리케이션 재시작

## 🔄 마이그레이션

기존 대용량 설정 파일을 새 구조로 마이그레이션:

```bash
python config_manager.py migrate archived/startup_config_20250719_110326.json
```

## ⚡ 성능 개선

- **개별 로딩**: 필요한 전략만 선택적으로 로드 가능
- **캐시**: 설정 로더에서 자동 캐싱 지원
- **유효성 검사**: 설정 오류 사전 감지
- **타입 안전성**: 구조화된 설정으로 런타임 오류 방지

## 🐛 문제 해결

### 설정 로드 실패
```bash
python config_manager.py validate
```

### 레거시 파일 사용
```python
from strategy_configs.config_loader import StrategyConfigLoader
loader = StrategyConfigLoader()
configs = loader.load_legacy_config_file('archived/old_config.json')
```

### 로그 확인
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# 상세한 로드 과정 확인 가능
```

---

이 새로운 구조는 전략 설정의 관리성, 확장성, 유지보수성을 크게 향상시킵니다. 
각 전략을 독립적으로 관리할 수 있으며, 필요에 따라 선택적으로 로드할 수 있습니다.