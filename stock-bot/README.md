# 📈 Stock Analysis & Trading Bot

본 프로젝트는 미국 주식 시장을 위한 데이터 기반의 정교한 자동 분석 및 트레이딩 신호 감지 시스템입니다. 최신 소프트웨어 아키텍처(DDD)를 적용하여, 복잡한 금융 데이터를 체계적으로 처리하고 유연한 투자 전략을 실행 및 검증할 수 있도록 설계되었습니다.

## 🔑 주요 분석 결과: 만능 전략은 없다 (Key Findings: No Silver Bullet)

최근 `AAPL`, `TSLA`, `QQQM` 등의 종목에 대한 2024-2025년 백테스팅을 통해 다음과 같은 중요한 통찰을 얻었습니다.

1.  **전략의 성과는 시장 상황에 따라 크게 달라집니다:** 동일한 전략이라도 특정 종목과 기간에 따라 성과가 극명하게 갈렸습니다. 예를 들어, `CONSERVATIVE`와 `MEAN_REVERSION` 전략은 2025년 AAPL 시장에서는 손실을 기록했지만, 2024년 TSLA 시장에서는 유의미한 수익을 창출했습니다. 이는 각 시장의 특성(변동성, 추세)에 맞는 전략을 선택하는 것이 매우 중요함을 시사합니다.

2.  **`MARKET_REGIME_HYBRID` 전략의 발견:**
    *   **TSLA**와 같이 변동성이 매우 크고 추세가 자주 바뀌는 개별 주식에��는, 시장 체제를 진단하여 최적의 하위 전략을 동적으로 선택하는 **`MARKET_REGIME_HYBRID`** 전략이 **+33.22%**의 높은 수익률과 **-17.52%**의 상대적으로 낮은 최대 낙폭을 기록하며 최고의 성과를 보였습니다.
    *   반면, **QQQM**과 같은 안정적인 시장 지수 ETF에서는 **`CONSERVATIVE_REVERSION_HYBRID`** 전략이 **-0.83%**의 손실과 **-3.58%**라는 경이로운 수준의 최대 낙폭을 기록하며, 수익 창출보다는 **자본 보존**에 매우 뛰어난 성능을 보였습니다.
    *   이는 "최고의 전략"이란 하나만 존재하는 것이 아니라, **투자의 목표(수익 극대화 vs 안정성)와 대상 자산의 특성에 맞는 최적의 도구를 선택해야 함**을 의미합니다.

3.  **`QUALITY_TREND` 전략의 공식 폐기:**
    *   해당 전략은 분석에 필수적인 재무 데이터를 현재 시스템이 지원하지 않아, 사실상 동작하지 않는 것으로 확인되었습니다. 이에 따라 시스템에서 공식적으로 제거하여 혼란의 여지를 없앴습니다.

## 💎 핵심 기능 상세 분석

### **1. 다층적 기술적 분석 및 신호 감지 (The Analysis Engine)**

이 시스템의 두뇌는 원본 데이터를 몇 단계에 걸쳐 정제하고 분석하여 최종 투자 신호를 생성합니다. 이 다층적 분석 과정은 신호의 신뢰도를 높이고, 모든 결정을 투명하게 추적할 수 있도록 설계되었습니다.

#### **프로세스 개요**

`[Raw Data] -> ① 지표 계산 -> ② 개별 신호 감지 -> ③ 복합 신호 생성 -> ④ 가중 점수화 -> ⑤ 최종 결정 및 근거 기록 -> [BUY/SELL Signal]`

---

### **2. 유연한 투자 전략 엔진 (The Strategy Engine)**

이 시스템의 진정한 강점은 단일 알고리즘이 아닌, 다양한 분석 모델(전략)을 상황에 맞게 선택하고 조합할 수 있는 유연한 전략 엔진에 있습니다. 이 엔진 덕분에 시장 변화에 능동적으로 대응할 수 있습니다.

#### **세 가지 분석 모드**

1.  **정적 전략 모드 (Static Strategy Mode):**
    *   가장 기본적인 모드로, 내장된 전략 중 사용자가 명시적으로 선택한 하나의 전략(예: `MOMENTUM`)을 사용하여 일관된 규칙으로 분석을 수행합니다.

2.  **전략 조합 모드 (Strategy Mix Mode):**
    *   하나의 전략에만 의존하는 위험을 줄이기 위해, 여러 정적 전략을 동시에 실행하고 그 결과를 조합(앙상블)하는 모드입니다. 예를 들어, `conservative_mix`는 `CONSERVATIVE`와 `TREND_FOLLOWING` 전략이 모두 동의하는 신호만 채택���는 **투표(Voting)** 방식을 사용합니다.

3.  **동적 전략 모드 (Dynamic Strategy Mode) - [컨셉/개발중]**
    *   가장 진보된 모드로, 미리 정해진 규칙을 넘어 시장 상황에 실시간으로 반응하여 스스로 분석 로직을 수정합니다.

### **3. 전략 시뮬레이션 및 성과 검증 (The Backtesting Engine)**

아무리 정교한 전략이라도, 과거 데이터에 기반한 엄격한 검증 없이는 신뢰할 수 없습니다. 이 시스템의 백테스팅 엔진은 다양한 시나리오 하에 전략의 성과를 가상으로 시뮬레이션하여, 객관적인 데이터로 전략의 잠재적 수익성과 위험성을 평가하는 핵심적인 역할을 수행합니다.

#### **핵심 성과 지표 (Key Performance Indicators)**

| 지표 (KPI) | 설명 |
| :--- | :--- |
| **총수익률 (Total Return)** | 투자 기간 동안의 누적 수익률입니다. |
| **연환산 수익률 (Annualized Return)** | 변동성을 고려하여 수익률을 연 단위로 표준화한 값입니다. |
| **최대 낙폭 (Max Drawdown)** | 투자 기간 중 자산이 최고점에서 최저점까지 하락한 가장 큰 비율로, 전략이 가진 내재적 위험을 보여주는 핵심 지표입니다. |
| **샤프 지수 (Sharpe Ratio)** | 위험 대비 수익성을 나타내는 지표로, 감수�� 1단위의 위험에 대해 어느 정도의 초과 수익을 얻었는지를 측정합니다. 높을수록 효율적인 전략입니다. |
| **승률 (Win Rate)** | 전체 거래 중 수익을 낸 거래의 비율입니다. |
| **수익 팩터 (Profit Factor)** | 총수익을 총손실로 나눈 값으로, 1보다 클수록 수익성이 높음을 의미합니다. |

---

## 🛠️ The Strategies: Built-in & Custom Models

시스템에는 다음과 같은 정적 전략이 내장되어 있으며, `run_backtest.py` 실행 시 선택하여 사용할 수 있습니다.

| 전략명 (Enum) | 핵심 특징 |
| :--- | :--- |
| **CONSERVATIVE** | 안정성 최우선, 초강력 신호만 감지 |
| **BALANCED** | 안정성과 수익성의 균형 |
| **AGGRESSIVE** | 적극적 거래, 약한 신호도 포착 |
| **MOMENTUM** | RSI, Stoch 등 모멘텀 지표 중심 |
| **TREND_FOLLOWING** | SMA, MACD 등 추세 지표 중심 |
| **CONTRARIAN** | 과매도/과매수 구간에서의 반전 탐색 |
| **SCALPING** | 초단기 매매, 거래량 신호 중시 |
| **SWING** | 며칠간의 중기적 가격 변동 활용 |
| **MEAN_REVERSION** | 볼린저 밴드 기반 평균 회귀 경향 이용 |
| **TREND_PULLBACK** | 상승 추세 중 눌림목 매수 타이밍 포착 |
| **VOLATILITY_BREAKOUT**| 변동성 돌파 시점을 거래량과 함께 포착 |
| **MULTI_TIMEFRAME** | 장기(일봉)와 단기(시간봉) 추세를 함께 확인 |
| **MACRO_DRIVEN** | VIX, 버핏 지수를 분석에 통합 |
| **ADAPTIVE_MOMENTUM** | `TREND_FOLLOWING`과 `MOMENTUM` 전략을 결합 |
| **CONSERVATIVE_REVERSION_HYBRID** | `CONSERVATIVE`와 `MEAN_REVERSION` 전략을 결합 (자본 보존에 특화) |
| **MARKET_REGIME_HYBRID** | 시장 체제를 진단하여 최적의 하위 전략(추세/변동성/평균회귀)을 동적으로 선택 |

---

## 🚀 Usage: Backtesting Your Strategies

`run_backtest.py` 스크립트를 통해 다양한 방식으로 전략을 검증할 수 있습니다.

**1. 특정 전략으로 백테스팅 (가장 일반적인 사용법)**
`python run_backtest.py --mode strategy --strategy AGGRESSIVE --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01`

**2. 여러 전략의 성과 비교**
`python run_backtest.py --mode strategy-comparison --compare-strategies CONSERVATIVE BALANCED MOMENTUM --tickers WM --start-date 2024-01-01 --end-date 2025-01-01`

**3. 전략 조합(Mix)으로 백테스팅**
`python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix --tickers WM --start-date 2024-01-01 --end-date 2025-01-01`

모든 백테스팅 결과는 `./backtest_results/` 디렉토리에 상세 정보가 담긴 `JSON` 파일로 자동 저장됩니다.

### **과거 시장 데이터 채우기 (백필링)**

시스템의 정확도를 높이거나, 장기간의 데이터 분석을 위해 과거의 누락된 시장 지표 데이터를 채워 넣을 수 있습니다. 이 기능은 독립된 `market_data_backfiller` 패키지를 통해 제공됩니다.

**1. 특정 기간 동안 기본 설정된 모든 지표 채우기**
`python -m domain.market_data_backfiller.backfiller --start_date 2023-01-01 --end_date 2023-12-31`

**2. 특정 지표만 골라서 채우기**
`python -m domain.market_data_backfiller.backfiller --start_date 2024-01-01 --end_date 2024-06-30 --indicators VIX DXY`

- 백필할 지표 목록은 `domain/market_data_backfiller/config.py` 파일의 `ENABLED_PROVIDERS` 리스트에서 기본값을 수정할 수 있습니다.

#### ⚠️ 데이터베이스 스키마 동기화 (Database Schema Sync)
새로운 시장 지표(`MarketIndicatorType`)를 코드에 추가할 경우, 데이터베이스 스키마도 함께 업데이트해야 합니다. 특히 `market_data` 테이블의 `indicator_type` `ENUM` 목록에 새로운 지표 이름을 추가��야 합니다. 스키마가 동기화되지 않으면, 백필러가 해당 지표 데이터를 저장하지 못할 수 있습니다. (e.g., `ALTER TABLE market_data MODIFY COLUMN indicator_type ENUM(...) NOT NULL;`)

## 🏗️ Architecture

*   **Domain-Driven Design (DDD)**: 비즈니스 로직(`domain`)과 기술적 구현(`infrastructure`)을 명확히 분리하여 유지보수성과 확장성을 극대화했습니다.
*   **Repository Pattern**: 데이터 영속성 처리를 추상화하여, 데이터베이스 기술이 변경되어도 비즈니스 로직은 영향을 받지 않도록 설계되었습니다.
*   **Scheduler**: `APScheduler`를 사용하여 모든 자동화 작업을 중앙에서 관리하고 실행합니다.

### 아키텍처 주요 변경사항 (Architecture Highlights)

최근 코드베이스의 ��지보수성과 확장성을 높이기 위해 다음과 같은 주요 리팩토링이 진행되었습니다.

#### 1. 전략 구현 모듈화 (Strategy Implementation Modularization)
- 기존의 거대했던 `strategy_implementations.py` 파일을 각 전략 클래스별로 하나의 파일로 분리하여 `domain/analysis/strategy/implementations/` 디렉토리 아래로 이동시켰습니다.
- 이를 통해 개별 전략의 코드를 더 쉽게 찾고 수정할 수 있게 되었습니다.

#### 2. 클래스 역할 및 책임 분리 (SOLID 원칙 강화)
- `StrategyFactory`, `StrategyManager`, `StrategySelector` 클래스의 역할을 명확히 분리하여 단일 책임 원칙(SRP)을 강화했습니다.
  - **`StrategyFactory` (생성자):** 오직 전략의 **인스턴스 생성**만을 책임집니다.
  - **`StrategySelector` (정보 제공자/추천자):** 설정 파일을 기반으로 사용 가능한 전략의 **정보를 제공**하고, 특정 조건에 **가장 적합한 전략을 추천**하는 역할을 전담합니다.
  - **`StrategyManager` (실행 관리자):** `Selector`의 추천을 받아, `Factory`를 통해 생성된 전략 인스턴스의 **실행과 생명주기를 관리**합니다.

## 📦 Installation

1.  **Clone the repository:**
    `git clone <repository-url>`
    `cd stock-bot`

2.  **Install dependencies:**
    `pip install -r requirements.txt`

3.  **Run the system:**
    *   백테스팅만 실행할 경우: `run_backtest.py` 사용
    *   스케줄러를 포함한 전체 시스템을 실행할 경우: `python main.py`