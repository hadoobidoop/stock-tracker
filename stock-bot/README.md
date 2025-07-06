# 📈 Stock Analysis & Trading Bot

본 프로젝트는 미국 주식 시장을 위한 데이터 기반의 정교한 자동 분석 및 트레이딩 신호 감지 시스템입니다. 최신 소프트웨어 아키텍처(DDD)를 적용하여, 복잡한 금융 데이터를 체계적으로 처리하고 유연한 투자 전략을 실행 및 검증할 수 있도록 설계되었습니다.

## 💎 핵심 기능 상세 분석

### **1. 다층적 기술적 분석 및 신호 감지 (The Analysis Engine)**

이 시스템의 두뇌는 원본 데이터를 몇 단계에 걸쳐 정제하고 분석하여 최종 투자 신호를 생성합니다. 이 다층적 분석 과정은 신호의 신뢰도를 높이고, 모든 결정을 투명하게 추적할 수 있도록 설계되었습니다.

#### **프로세스 개요**

```
[Raw Data] -> ① 지표 계산 -> ② 개별 신호 감지 -> ③ 복합 신호 생성 -> ④ 가중 점수화 -> ⑤ 최종 결정 및 근거 기록 -> [BUY/SELL Signal]
```

---

#### **① 단계: 기술적 지표 계산 (Indicator Calculation)**

모든 분석은 표준 OHLCV 데이터에 다양한 기술적 지표를 계산하여 추가하는 것에서 시작됩니다.

*   **관련 코드:** `domain/analysis/utils/technical_indicators.py`
*   **핵심 함수:** `calculate_all_indicators(df)`

이 함수는 내부적으로 `calculate_sma`, `calculate_rsi` 등 여러 개별 지표 계산 함수를 호출하여 데이터프레임에 지표 컬럼을 추가합니다.

```python
# domain/analysis/utils/technical_indicators.py
def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # ...
    df = calculate_sma(df, sma_periods)
    df = calculate_rsi(df, rsi_period)
    df = calculate_macd(df, macd_fast, macd_slow, macd_signal)
    # ...
    return df
```

| 계산되는 주요 지표 | 약어/종류 | 설명 |
| :--- | :--- | :--- |
| **이동평균선** | SMA | 주가의 단기, 중기, 장기 추세를 파악하는 가장 기본적인 지표입니다. |
| **상대강도지수** | RSI | 주가의 상승 압력과 하락 압력 간의 상대적인 강도를 나타내며, 과매수/과매도 상태를 판단합니다. |
| **MACD** | - | 단기 지수이동평균과 장기 지수이동평균 간의 관계를 통해 추세의 방향과 강도를 측정합니다. |
| **스토캐스틱** | %K, %D | 특정 기간 동안의 주가 변동 범위에서 현재 주가의 위치를 나타내어 과매수/과매도를 판단합니다. |
| **볼린저 밴드** | BBands | 주가의 변동성을 측정하며, 밴드 상단과 하단은 잠재적인 지지/저항선으로 작용합니다. |
| **ADX** | - | 추세의 강도를 측정하는 지표로, 추세의 존재 여부를 판단하는 데 도움을 줍니다. (추세의 방향은 알려주지 않음) |
| **ATR** | - | 주가의 변동성 크기를 측정하며, 주로 손절매 가격을 설정하는 데 활용됩니다. |
| **거래량 이동평균**| Volume SMA | 평균적인 거래량 대비 현재 거래량의 수준을 파악하여 신호의 신뢰도를 검증합니다. |

---

#### **② 단계: 개별 신호 감지 (Atomic Signal Detection)**

계산된 각 기술적 지표는 개별 '감지기(Detector)'에 의해 해석되어, "RSI 과매도"와 같은 원자적(Atomic)인 1차 신호를 생성합니다.

*   **관련 코드:** `domain/analysis/detectors/` 하위 디렉토리 (예: `momentum/rsi_detector.py`)
*   **핵심 클래스:** `RSISignalDetector`, `MACDSignalDetector` 등 각 지표별 `*SignalDetector` 클래스

각 Detector는 `detect_signals` 메소드 내에서 자신만의 논리로 신호를 판단합니다.

```python
# domain/analysis/detectors/momentum/rsi_detector.py
class RSISignalDetector(BaseSignalDetector):
    def detect_signals(self, df: pd.DataFrame) -> tuple:
        # ...
        if latest_rsi < self.oversold_threshold:
            buy_score = self.weight * (self.oversold_threshold - latest_rsi) / 10
        # ...
        return buy_score, sell_score, buy_details, sell_details
```

---

#### **③ 단계: 복합 신호 생성 (Composite Signal Generation)**

더 높은 신뢰도를 위해, 2단계에서 생성된 여러 개의 개별 신호들을 논리적으로 조합하여 '복합 신호'를 만듭니다.

*   **관련 코드:** `domain/analysis/config/strategy_settings.py`
*   **핵심 설정:** `COMPOSITE_DETECTOR_CONFIG`

이 설정은 어떤 개별 감지기들을 어떤 조건(AND/OR)으로 묶을지를 정의하는 데이터입니다.

```python
# domain/analysis/config/strategy_settings.py
COMPOSITE_DETECTOR_CONFIG = {
    'MACD_Volume_Confirm': {
        'sub_detectors': ['MACDSignalDetector', 'VolumeSignalDetector'],
        'condition': 'AND'
    },
    'Any_Momentum': {
        'sub_detectors': ['RSISignalDetector', 'StochSignalDetector'],
        'condition': 'OR'
    }
}
```

---

#### **④ 단계: 전략 기반 가중 점수화 (Strategy-based Weighted Scoring)**

모든 신호가 동일한 중요도를 갖지는 않습니다. 현재 선택된 **투자 전략**에 따라 각 신호에 서로 다른 가중치가 부여되고, 이를 합산하여 최종 '신호 점수'를 계산합니다.

*   **관련 코드:** `domain/analysis/strategy/base_strategy.py`, `strategy_implementations.py`
*   **핵심 로직:** 각 전략(`UniversalStrategy`)은 `_adjust_score_by_strategy` 메소드를 통해 기본 점수를 자신의 스타일에 맞게 조정합니다.

```python
# domain/analysis/strategy/strategy_implementations.py
class UniversalStrategy(BaseStrategy):
    def _adjust_score_by_strategy(self, base_score: float, ...) -> float:
        # ...
        if self.strategy_type == StrategyType.TREND_FOLLOWING:
            # 추세 일치 시 점수 가중
            if market_trend == long_term_trend:
                adjusted_score *= 1.1
        # ...
        return adjusted_score
```

---

#### **⑤ 단계: 최종 결정 및 근거 기록 (Final Decision & Evidence)**

최종 신호 점수가 전략에 설정된 임계값(`signal_threshold`)을 초과하면, 비로소 **'매수(BUY)'** 또는 **'매도(SELL)'** 결정이 내려집니다. 이때, 모든 의사결정 과정이 투명하게 기록됩니다.

*   **관련 코드:** `domain/analysis/models/trading_signal.py`
*   **핵심 클래스:** `SignalEvidence`

이 데이터 클래스는 어떤 지표가 어떤 값으로 신호에 기여했는지 등 모든 근거를 담는 컨테이너 역할을 합니다.

```python
# domain/analysis/models/trading_signal.py
@dataclass
class SignalEvidence:
    signal_timestamp: datetime
    ticker: str
    final_score: int
    technical_evidences: List[TechnicalIndicatorEvidence] = field(default_factory=list)
    # ...
```

이러한 상세한 근거 기록은 모든 투자 결정의 이유를 명확히 설명하고, 향후 전략을 개선하는 데 매우 중요한 데이터를 제공합니다.

### **2. 유연한 투자 전략 엔진 (The Strategy Engine)**

이 시스템의 진정한 강점은 단일 알고리즘이 아닌, 다양한 분석 모델(전략)을 상황에 맞게 선택하고 조합할 수 있는 유연한 전략 엔진에 있습니다. 이 엔진 덕분에 시장 변화에 능동적으로 대응할 수 있습니다.

#### **엔진의 핵심 구성요소**

*   **`StrategyManager` (전략 관리자)**
    *   **위치:** `domain/analysis/strategy/strategy_manager.py`
    *   **역할:** 모든 전략(정적/동적)을 메모리에 로드하고 관리하는 중앙 관제탑입니다. 실시간으로 전략을 교체(`switch_strategy`)하고, 현재 시장 상황에 가장 적합한 분석 모델을 선택하여 실행을 명령하는 **"핫스왑(Hot-swapping)"** 기능을 제공합니다.

    ```python
    # domain/analysis/strategy/strategy_manager.py
    class StrategyManager:
        def switch_strategy(self, strategy_type: StrategyType) -> bool:
            if strategy_type not in self.active_strategies:
                return False
            self.current_strategy = self.active_strategies[strategy_type]
            return True
    ```

*   **`StrategyFactory` & `UniversalStrategy` (전략 공장 & 범용 전략)**
    *   **위치:** `domain/analysis/strategy/strategy_implementations.py`
    *   **역할:** 14개의 정적 전략을 14개의 다른 코드로 구현하는 대신, 단 하나의 `UniversalStrategy`와 `strategy_settings.py`라는 설정 파일을 사용합니다. `StrategyFactory`가 설정 파일을 읽어 `UniversalStrategy`에 주입하면, 마치 다른 전략인 것처럼 작동하는 매우 효율적인 **데이터 주도 설계(Data-Driven Design)**입니다. 이는 새로운 전략을 코드 변경 없이 설정 추가만으로 확장할 수 있게 합니다.

    ```python
    # domain/analysis/strategy/strategy_implementations.py
    class StrategyFactory:
        @classmethod
        def create_static_strategy(cls, strategy_type: StrategyType, ...) -> Optional[BaseStrategy]:
            config = get_strategy_config(strategy_type) # 설정 파일에서 전략의 파라미터를 가져옴
            # ...
            strategy = UniversalStrategy(strategy_type, config) # 범용 클래스에 설정을 주입하여 생성
            return strategy
    ```

#### **세 가지 분석 모드**

전략 엔진은 크게 세 가지 모드로 작동할 수 있습니다.

1.  **정적 전략 모드 (Static Strategy Mode):**
    *   가장 기본적인 모드로, 14개의 내장 전략 중 사용자가 명시적으로 선택한 하나의 전략(예: `MOMENTUM`)을 사용하여 일관된 규칙으로 분석을 수행합니다.

2.  **전략 조합 모드 (Strategy Mix Mode):**
    *   하나의 전략에만 의존하는 위험을 줄이기 위해, 여러 정적 전략을 동시에 실행하고 그 결과를 조합(앙상블)하는 모드입니다. 예를 들어, 5개의 전략 중 3개 이상이 동의하는 신호만 채택하는 **투표(Voting)** 방식을 사용하거나, 각 전략의 신뢰도에 따라 **가중 평균(Weighted Average)**을 내어 최종 결정을 내릴 수 있습니다.

3.  **동적 전략 모드 (Dynamic Strategy Mode) - [컨셉/개발중]**
    *   가장 진보된 모드로, 미리 정해진 규칙을 넘어 시장 상황에 실시간으로 반응하여 스스로 분석 로직을 수정합니다. 이는 **모디파이어(Modifiers)** 라는 강력한 개념을 통해 구현됩니다.
    *   **모디파이어란?** 특정 시장 조건을 감시하다가, 조건이 충족되면 분석 과정에 개입하는 '규칙'입니다.
        *   **위치:** `domain/analysis/strategy/modifiers.py`
        *   **예시 1 (VETO):** `VixOver30Modifier`는 VIX 지수가 30을 넘어서면(시장의 공포가 극심하면), 모든 매수 신호를 **거부(Veto)**하는 규칙을 적용할 수 있습니다.
        *   **예시 2 (ADJUST_WEIGHTS):** `BuffettOverheatedModifier`는 버핏 지수가 120%를 넘어서면(시장이 과열되었다고 판단되면), 공격적인 모멘텀 지표의 가중치를 자동으로 낮추고, 안정적인 가치 지표의 가중치를 높이도록 분석 로직을 **수정(Adjust)**할 수 있습니다.

    ```python
    # domain/analysis/strategy/modifiers.py
    class MarketIndicatorModifier(BaseModifier):
        def apply_action(self, context: DecisionContext, ...):
            action = self.definition.action
            if action.type == ModifierActionType.VETO_BUY:
                context.set_veto(ModifierActionType.VETO_BUY, ...)
            elif action.type == ModifierActionType.ADJUST_WEIGHTS:
                context.adjust_weight(...)
    ```

### **3. 전략 시뮬레이션 및 성과 검증 (The Backtesting Engine)**

아무리 정교한 전략이라도, 과거 데이터에 기반한 엄격한 검증 없이는 신뢰할 수 없습니다. 이 시스템의 백테스팅 엔진은 다양한 시나리오 하에 전략의 성과를 가상으로 시뮬레이션하여, 객관적인 데이터로 전략의 잠재적 수익성과 위험성을 평가하는 핵심적인 역할을 수행합니다.

#### **백테스팅 프로세스**

백테스팅은 `domain/backtesting/service/backtesting_service.py`의 `BacktestingService`에 의해 조율되며, 실제 시뮬레이션은 `domain/backtesting/engine/backtesting_engine.py`의 `BacktestingEngine`에서 수행됩니다.

1.  **데이터 로딩:** 사용자가 지정한 종목과 기간에 해당하는 과거 시세 데이터를 준비합니다.
2.  **시간 순 시뮬레이션:** 엔진은 과거 데이터의 첫날부터 마지막 날까지, 시간 순서대로(예: 하루씩) 이동하며 가상 거래를 실행합니다.

    ```python
    # domain/backtesting/engine/backtesting_engine.py
    class BacktestingEngine:
        def run_backtest(self, data: pd.DataFrame, strategy: BaseStrategy, ...) -> BacktestResult:
            # ...
            for index, row in data.iterrows():
                # ...
                signal_result = strategy.analyze(current_data, ...)
                # ...
                # 포트폴리오 업데이트 및 거래 기록
            # ...
            return result
    ```

3.  **신호 생성 및 가상 거래:** 각 시점마다, 엔진은 `StrategyManager`에게 현재 데이터에 대한 분석을 요청하여 매수/매도 신호를 받습니다. 신호가 발생하면, `domain/backtesting/models/portfolio.py`의 `Portfolio` 객체를 통해 가상의 포트폴리오 상태(현금, 주식 보유량)를 변경하는 **가상 거래(Virtual Trade)**를 기록합니다.
4.  **성과 계산:** 시뮬레이션이 끝나면, 전체 거래 기록과 자산 변화를 바탕으로 아래와 같은 상세한 성과 지표를 계산하여 최종 리포트를 생성합니다.

#### **핵심 성과 지표 (Key Performance Indicators)**

백테스팅 결과는 `domain/backtesting/models/backtest_result.py`의 `BacktestResult` 데이터 클래스에 담겨 반환되며, 다음과 같은 전문적인 지표들이 포함되어 다각도로 전략을 평가할 수 있게 합니다.

```python
# domain/backtesting/models/backtest_result.py
@dataclass
class BacktestResult:
    total_return_percent: float
    annualized_return_percent: float
    max_drawdown_percent: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    # ...
```

| 지표 (KPI) | 설명 |
| :--- | :--- |
| **총수익률 (Total Return)** | 투자 기간 동안의 누적 수익률입니다. |
| **연환산 수익률 (Annualized Return)** | 변동성을 고려하여 수익률을 연 단위로 표준화한 값입니다. |
| **최대 낙폭 (Max Drawdown)** | 투자 기간 중 자산이 최고점에서 최저점까지 하락한 가장 큰 비율로, 전략이 가진 내재적 위험을 보여주는 핵심 지표입니다. |
| **샤프 지수 (Sharpe Ratio)** | 위험 대비 수익성을 나타내는 지표로, 감수한 1단위의 위험에 대해 어느 정도의 초과 수익을 얻었는지를 측정합니다. 높을수록 효율적인 전략입니다. |
| **승률 (Win Rate)** | 전체 거래 중 수익을 낸 거래의 비율입니다. |
| **수익 팩터 (Profit Factor)** | 총수익을 총손실로 나눈 값으로, 1보다 클수록 수익성이 높음을 의미합니다. |

#### **다양한 실행 모드**

사용자는 `run_backtest.py` 스크립트를 통해 다음과 같은 다양한 모드로 백테스팅을 실행할 수 있습니다. `run_backtest.py`는 `--mode` 인수를 통해 어떤 백테스팅을 실행할지 결정합니다.

```python
# run_backtest.py
def main():
    args = parse_arguments()
    service = BacktestingService()
    if args.mode == 'strategy':
        run_strategy_backtest(service, args)
    elif args.mode == 'strategy-comparison':
        run_strategy_comparison(service, args)
    # ...
```

*   **단일 전략 분석 (`--mode strategy`):** 14개의 전략 중 하나를 지정하여 상세히 분석합니다.
*   **전략 비교 분석 (`--mode strategy-comparison`):** 여러 전략을 동시에 실행하여 성과를 비교하고 순위를 매깁니다.
*   **전략 조합 분석 (`--mode strategy-mix`):** 여러 전략을 앙상블한 모델의 성과를 검증합니다.
*   **거시 지표 전략 분석 (`--mode macro-analysis`):** 거시 경제 지표를 활용하는 `MACRO_DRIVEN` 전략을 다른 주요 전략들과 심층 비교합니다.

---

## 🌟 Core Concepts

### **4. 실시간 운영 및 알림 (Live Operation & Notification)**

백테스팅을 통해 검증된 전략은 `main.py`를 실행함으로써 실제 시장에서 자동으로 운영됩니다. 시스템은 중앙 스케줄러를 통해 24시간 쉬지 않고 시장을 감시하고, 정해진 로직에 따라 분석을 수행하며, 중요한 이벤트 발생 시 사용자에게 알릴 수 있는 기반을 갖추고 있습니다.

#### **자동화의 핵심: 스케줄러와 잡(Jobs)**

이 시스템의 심장은 `APScheduler`를 기반으로 하는 중앙 스케줄러입니다. `main.py`가 시작되면, `infrastructure/scheduler/scheduler_manager.py`의 `setup_scheduler()` 함수가 5개의 핵심 잡(Job)을 각각의 스케줄에 맞춰 등록하고 백그라운드에서 자동으로 실행합니다.

*   **관련 코드:** `infrastructure/scheduler/scheduler_manager.py`, `infrastructure/scheduler/jobs/`
*   **핵심 함수:** `setup_scheduler()`, `start_scheduler()`

```python
# infrastructure/scheduler/scheduler_manager.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def setup_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.timezone(settings.TIMEZONE))
    # 각 잡(Job)을 Cron 스케줄에 따라 등록
    scheduler.add_job(
        update_stock_metadata_job,
        trigger=CronTrigger(**settings.METADATA_UPDATE_JOB['cron']),
        # ...
    )
    # ... 다른 잡들 등록 ...
    return scheduler

def start_scheduler(scheduler):
    try:
        scheduler.start()
        # ...
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
```

| 잡 (Job) | 실행 주기 (뉴욕 시간) | 주요 역할 |
| :--- | :--- | :--- |
| **`realtime_signal_detection_job`** | 장중 매 30분 | **(핵심)** `infrastructure/scheduler/jobs/realtime_signal_detection_job.py`에 정의되어 있으며, 최신 시세 데이터로 현재 전략을 실행하여, 실시간 매매 신호를 감시합니다. |
| `hourly_ohlcv_update_job` | 장중 매시 10분 | `infrastructure/scheduler/jobs/hourly_ohlcv_update_job.py`에 정의되어 있으며, 실시간 분석에 필요한 시간봉 데이터를 업데이트합니다. |
| `daily_ohlcv_update_job` | 매일 오후 5:00 | `infrastructure/scheduler/jobs/daily_ohlcv_update_job.py`에 정의되어 있으며, 장 마감 후 일봉 데이터를 업데이트합니다. |
| `market_data_update_job` | 매일 오후 6:00 | `infrastructure/scheduler/jobs/market_data_update_job.py`에 정의되어 있으며, 버핏 지수, VIX 등 모든 거시 경제 지표를 업데이트합니다. |
| `update_stock_metadata_job` | 매주 월요일 오전 2:30 | `infrastructure/scheduler/jobs/update_stock_metadata_job.py`에 정의되어 있으며, 분석 대상 종목 리스트 등 기본 정보를 업데이트합니다. |

#### **알림 서비스 (Notification Service) - [확장 가능]**

`domain/notification` 디렉토리는 향후 알림 기능 확장을 위한 구조를 제공합니다. 현재 `domain/notification/service/notification_dispatch_service.py` 파일은 비어있지만, 이 구조를 활용하여 `realtime_signal_detection_job`과 연동하면 다음과 같은 시나리오를 쉽게 구현할 수 있습니다.

*   **신규 신호 알림:** 새로운 매수/매도 신호가 발생했을 때, 사용자의 이메일이나 슬랙(Slack)으로 즉시 알림을 보냅니다.
    *   *예시: "AAPL에 대해 MOMENTUM 전략 기반의 매수 신호(점수: 8.5)가 발생했습니다."*
*   **중요 시장 변화 알림:** VIX 지수가 급등하거나 시장이 급락하는 등 중요한 거시적 변화가 감지되었을 때 경고 알림을 보냅니다.

---

## 🌟 Core Concepts

이 시스템은 몇 가지 핵심 개념을 바탕으로 운영됩니다.

1.  **정적 전략 (Static Strategy)**
    *   미리 정의된 고정된 규칙에 따라 투자 결정을 내리는 방식입니다. `CONSERVATIVE`(보수적), `BALANCED`(균형), `AGGRESSIVE`(공격적) 등 14개의 개별 전략이 구현되어 있으며, 각 전략은 서로 다른 지표 가중치, 리스크 허용도, 거래 빈도를 가집니다. 예측 가능하고 일관적인 분석이 필요할 때 사용됩니다.

2.  **전략 조합 (Strategy Mix)**
    *   여러 개의 정적 전략을 동시에 실행하여 그 결과를 종합(앙상블)하는 방식입니다. 예를 들어, 5개의 전략 중 4개 이상이 '매수' 신호를 보낼 때만 최종 '매수'로 판단하여, 단일 전략의 맹점을 보완하고 신호의 신뢰도를 높입니다.

3.  **동적 전략 (Dynamic Strategy) - [컨셉/개발중]**
    *   VIX 지수나 버핏 지수와 같은 시장 상황 인식 지표에 따라, 사용하는 기술적 지표의 가중치나 리스크를 실시간으로 조절하는 지능형 전략입니다. 현재는 개념이 정의되어 있으며, 백테스팅 코드에 향후 확장을 위한 플레이스홀더가 마련되어 있습니다.
    *   **주의:** `run_backtest.py`에서 `--mode dynamic-strategy`와 같은 관련 인수를 볼 수 있으나, 아직 기능이 완전히 구현되지 않았으므로 예상과 다르게 동작할 수 있습니다.

4.  **백테스팅 (Backtesting)**
    *   과거의 시장 데이터를 이용해 특정 투자 전략이 과거에 어떤 성과를 냈을지 시뮬레이션하는 과정입니다. 실제 투자를 집행하기 전에 전략의 유효성(수익률, 최대 낙폭, 승률 등)을 객관적인 데이터로 검증하는 핵심 기능입니다.

## ✨ Key Features

*   **다각화된 데이터 수집**: 개별 주식의 시세(일봉/시간봉)는 물론, 시장 전체를 조망하는 8가지 이상의 거시/시장 지표를 자동 수집합니다.
*   **14개의 내장 투자 전략**: 보수적, 공격적, 모멘텀, 추세 추종, 거시 지표 기반 등 다양한 투자 스타일을 지원하는 14개의 정적 전략을 제공합니다.
*   **강력한 백테스팅 엔진**: 특정 전략, 전략 조합, 자동 선택 등 다양한 모드로 과거 성과를 시뮬레이션하고 상세 리포트를 생성합니다.
*   **자동화된 운영**: 5개의 스케줄링된 배치 잡(Job)을 통해 데이터 수집, 분석, 신호 감지 등 모든 과정이 자동으로 실행됩니다.
*   **안정적인 인프라**: 도메인 주도 설계(DDD)를 채택하여 비즈니스 로직과 기술 구현을 분리했으며, 데이터 수집 시 이중화된 소스를 활용하여 안정성을 높였습니다.

---

## 📊 Data Universe: The Fuel for Analysis

본 시스템은 분석의 깊이와 정확성을 위해 다음과 같이 다각화된 데이터를 자동 수집 및 관리합니다.

| 데이터 종류 | 상세 항목 | 수집 주기 | 주요 소스 | 백업 소스/대안 |
| :--- | :--- | :--- | :--- | :--- |
| **주식 시세** | 일봉/시간봉 OHLCV | 매일/매시간 | Yahoo Finance | - |
| **시장 가치** | 버핏 지수 (Buffett Indicator) | 매일 | FRED (Fed Z.1) | Yahoo (^W5000) |
| **시장 심리** | VIX (변동성 지수) | 매일 | FRED (VIXCLS) | Yahoo (^VIX) |
| **시장 심리** | 공포와 탐욕 지수 (Fear & Greed) | 매일 | CNN API | VIX 기반 추정 |
| **옵션 시장** | 풋/콜 비율 (Put/Call Ratio) | 매일 | CBOE API | VIX 기반 추정 |
| **채권 시장** | 10년 만기 국채 수익률 | 매일 | FRED (DGS10) | - |
| **원자재** | 금(Gold) 선물 가격 | 매일 | Yahoo (GC=F) | - |
| **원자재** | WTI 원유(Crude Oil) 선물 가격 | 매일 | Yahoo (CL=F) | - |
| **시장 지수** | S&P 500 지수 | 매일 | Yahoo (^GSPC) | - |
| **주식 정보** | 종목 메타데이터 (섹터, 이름 등) | 매주 | (내부 관리) | - |

---

## 🛠️ The Strategies: 14 Built-in Models

시스템에는 다음과 같이 14개의 개별 정적 전략이 내장되어 있으며, `run_backtest.py` 실행 시 선택하여 사용할 수 있습니다.

| 전략명 (Enum) | 핵심 특징 | 리스크/보유기간 | 신호 임계값 |
| :--- | :--- | :--- | :--- |
| **CONSERVATIVE** | 안정성 최우선, 초강력 신호만 감지 | 1% / 72시간 | 12.0 (매우 높음) |
| **BALANCED** | 안정성과 수익성의 균형 | 2% / 48시간 | 8.0 (표준) |
| **AGGRESSIVE** | 적극적 거래, 약한 신호도 포착 | 3% / 24시간 | 5.0 (매우 낮음) |
| **MOMENTUM** | RSI, Stoch 등 모멘텀 지표 중심 | 2.5% / 36시간 | 6.0 (낮음) |
| **TREND_FOLLOWING** | SMA, MACD 등 추세 지표 중심 | 2% / 60시간 | 9.0 (높음) |
| **CONTRARIAN** | 과매도/과매수 구간에서의 반전 탐색 | 2% / 48시간 | 7.0 (표준) |
| **SCALPING** | 초단기 매매, 거래량 신호 중시 | 1.5% / 12시간 | 4.0 (매우 낮음) |
| **SWING** | 며칠간의 중기적 가격 변동 활용 | 2% / 96시간 | 8.0 (표준) |
| **MEAN_REVERSION** | 볼린저 밴드 기반 평균 회귀 경향 이용 | 1.5% / 36시간 | 7.5 (표준) |
| **TREND_PULLBACK** | 상승 추세 중 눌림목 매수 타이밍 포착 | 2% / 72시간 | 8.5 (높음) |
| **VOLATILITY_BREAKOUT**| 변동성 돌파 시점을 거래량과 함께 포착 | 2.5% / 48시간 | 7.0 (표준) |
| **QUALITY_TREND** | 여러 추세 지표가 모두 동의할 때만 진입 | 1% / 120시간 | 10.0 (매우 높음) |
| **MULTI_TIMEFRAME** | 장기(일봉)와 단기(시간봉) 추세를 함께 확인 | 2% / 96시간 | 9.0 (높음) |
| **MACRO_DRIVEN** | VIX, 버핏 지수를 분석에 통합 | 2% / 72시간 | 8.0 (표준) |

---

## ⚙️ Automated System: 5 Core Jobs

시스템은 `APScheduler`에 의해 관리되는 5개의 핵심 배치 잡(Job)을 통해 자동으로 운영됩니다. (뉴욕 시간 기준)

| 잡 (Job) | 실행 주기 | 주요 기능 |
| :--- | :--- | :--- |
| **`update_stock_metadata_job`** | 매주 월요일 오전 2:30 | S&P 500 종목 등 메타데이터 업데이트 |
| **`hourly_ohlcv_update_job`** | 장중 매시 10분 | 시간봉 시세 데이터 수집 |
| **`realtime_signal_detection_job`**| 장중 매 30분 간격 | 최신 데이터를 바탕으로 실시간 매매 신호 감지 |
| **`daily_ohlcv_update_job`** | 매일 오후 5:00 | 일봉 시세 데이터 수집 |
| **`market_data_update_job`** | 매일 오후 6:00 | 버핏 지수, VIX 등 모든 시장/거시 지표 업데이트 |

---

## 🚀 Usage: Backtesting Your Strategies

`run_backtest.py` 스크립트를 통해 다양한 방식으로 전략을 검증할 수 있습니다.

**1. 특정 전략으로 백테스팅 (가장 일반적인 사용법)**
```bash
# AGGRESSIVE 전략으로 AAPL, MSFT 종목을 백테스팅
python run_backtest.py --mode strategy --strategy AGGRESSIVE \
--tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

**2. 여러 전략의 성과 비교**
```bash
# 지정된 4개 전략의 성과를 비교하여 리포트 생성
python run_backtest.py --mode strategy-comparison \
--compare-strategies CONSERVATIVE BALANCED MOMENTUM MACRO_DRIVEN \
--tickers NVDA --start-date 2024-01-01 --end-date 2025-01-01
```

**3. 전략 조합(Mix)으로 백테스팅**
```bash
# 'balanced_mix' 조합으로 백테스팅
python run_backtest.py --mode strategy-mix --strategy-mix balanced_mix \
--tickers GOOGL --start-date 2024-01-01 --end-date 2025-01-01
```

**4. 거시 지표 기반 전략 심층 분석**
```bash
# MACRO_DRIVEN 전략을 다른 주요 전략들과 심층 비교 분석
python run_backtest.py --mode macro-analysis \
--tickers AAPL MSFT --start-date 2024-01-01 --end-date 2025-01-01
```

모든 백테스팅 결과는 `./backtest_results/` 디렉토리에 상세 정보가 담긴 `JSON` 파일로 자동 저장됩니다.

## 🏗️ Architecture

*   **Domain-Driven Design (DDD)**: 비즈니스 로직(`domain`)과 기술적 구현(`infrastructure`)을 명확히 분리하여 유지보수성과 확장성을 극대화했습니다.
    *   `domain`: 투자 전략, 신호 감지 규칙 등 순수한 비즈니스 로직.
    *   `infrastructure`: 데이터베이스 연동, 외부 API 클라이언트, 스케줄러 등 기술 구현.
*   **Repository Pattern**: 데이터 영속성 처리를 추상화하여, 데이터베이스 기술이 변경되어도 비즈니스 로직은 영향을 받지 않도록 설계되었습니다.
*   **Scheduler**: `APScheduler`를 사용하여 모든 자동화 작업을 중앙에서 관리하고 실행합니다.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd stock-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the system:**
    *   백테스팅만 실행할 경우: `run_backtest.py` 사용
    *   스케줄러를 포함한 전체 시스템을 실행할 경우:
        ```bash
        python main.py
        ```