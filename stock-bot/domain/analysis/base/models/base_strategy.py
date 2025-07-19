from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd

from domain.strategies.strategy_config import StrategyConfig
from domain.analysis.models.enums import StrategyType
from domain.analysis.models.trading_signal import TradingSignal, SignalType
from domain.analysis.models.strategy_result import StrategyResult
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


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
                daily_extra_indicators: Optional[Dict] = None) -> Dict:
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
        if hasattr(self.config, 'name'):
            return self.config.name
        elif isinstance(self.config, dict):
            return self.config.get('name', f"Strategy_{self.strategy_type.value}")
        else:
            return f"Strategy_{self.strategy_type.value}"

    def get_description(self) -> str:
        """전략 설명 반환"""
        if hasattr(self.config, 'description'):
            return self.config.description
        elif isinstance(self.config, dict):
            return self.config.get('description', f"Description for {self.strategy_type.value}")
        else:
            return f"Description for {self.strategy_type.value}"

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