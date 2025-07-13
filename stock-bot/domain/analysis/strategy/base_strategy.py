from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from dataclasses import dataclass
from datetime import datetime

from domain.analysis.models.trading_signal import TradingSignal, SignalType
from infrastructure.db.models.enums import TrendType
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyResult:
    """전략 실행 결과"""
    strategy_name: str
    strategy_type: StrategyType
    has_signal: bool
    total_score: float
    signal_strength: str  # "WEAK", "MODERATE", "STRONG"
    signals_detected: List[str]
    signal: Optional[TradingSignal] = None
    confidence: float = 0.0
    buy_score: float = 0.0
    sell_score: float = 0.0
    stop_loss_price: Optional[float] = None

    def __post_init__(self):
        """신호 강도 자동 계산"""
        if self.total_score >= 10:
            self.signal_strength = "STRONG"
        elif self.total_score >= 6:
            self.signal_strength = "MODERATE"
        else:
            self.signal_strength = "WEAK"

        self.confidence = min(self.total_score / 15.0, 1.0)  # 15점 만점 기준으로 정규화


class BaseStrategy(ABC):
    """전략 기본 추상 클래스"""

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        self.strategy_type = strategy_type
        self.config = config
        self.is_initialized = False

        # 성능 모니터링
        self.signals_generated = 0
        self.last_analysis_time: Optional[datetime] = None
        self.average_score = 0.0
        self.score_history: List[float] = []

    @abstractmethod
    def initialize(self) -> bool:
        """
        전략에 필요한 리소스(예: SignalOrchestrator)를 초기화합니다.
        각 구체적인 전략 클래스에서 구
        해야 합니다.
        """
        pass

    @abstractmethod
    def analyze(self,
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Optional[Dict] = None) -> StrategyResult:
        """
        데이터를 분석하여 거래 신호를 생성합니다.
        각 구체적인 전략 클래스에서 핵심 로직을 구현해야 합니다.
        """
        pass

    def _create_trading_signal(self, signal_result: Dict, ticker: str, score: float,
                             df_with_indicators: pd.DataFrame) -> TradingSignal:
        """
        공통 TradingSignal 객체 생성 로직
        """
        from domain.analysis.models.trading_signal import SignalEvidence

        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL

        evidence = SignalEvidence(
            signal_timestamp=datetime.now(),
            ticker=ticker,
            signal_type=signal_result.get('type', 'BUY'),
            final_score=int(score),
            raw_signals=signal_result.get('details', []),
            applied_filters=[f"Strategy: {self.get_name()}"],
            score_adjustments=[f"Strategy adjustment applied: {self.get_name()}"]
        )

        return TradingSignal(
            signal_id=None,
            ticker=ticker,
            signal_type=signal_type,
            signal_score=int(score),
            timestamp_utc=datetime.now(),
            current_price=df_with_indicators['Close'].iloc[-1],
            market_trend=TrendType(signal_result.get('market_trend', 'NEUTRAL')),
            long_term_trend=TrendType(signal_result.get('long_term_trend', 'NEUTRAL')),
            details=signal_result.get('details', []),
            stop_loss_price=signal_result.get('stop_loss_price'),
            evidence=evidence
        )

    def get_name(self) -> str:
        """전략 이름 반환"""
        return self.config.name

    def get_description(self) -> str:
        """전략 설명 반환"""
        return self.config.description

    def get_performance_metrics(self) -> Dict[str, Any]:
        """전략 성능 지표 반환"""
        return {
            'signals_generated': self.signals_generated,
            'average_score': self.average_score,
            'last_analysis_time': self.last_analysis_time,
            'score_history_length': len(self.score_history),
            'is_initialized': self.is_initialized,
            'signal_threshold': self.config.signal_threshold,
            'risk_per_trade': self.config.risk_per_trade
        }

    def reset_performance_metrics(self):
        """성능 지표 초기화"""
        self.signals_generated = 0
        self.score_history.clear()
        self.average_score = 0.0
        self.last_analysis_time = None

    def can_generate_signal(self, current_time: datetime) -> bool:
        """현재 신호를 생성할 수 있는지 확인 (쿨다운 체크 등)"""
        if self.last_analysis_time is None:
            return True

        # 최소 간격 체크 (예: 5분)
        min_interval_minutes = 5
        time_diff = current_time - self.last_analysis_time
        return time_diff.total_seconds() >= min_interval_minutes * 60 