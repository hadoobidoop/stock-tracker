from dataclasses import dataclass
from typing import List, Optional

from domain.analysis.models.trading_signal import TradingSignal
from domain.analysis.models.enums import StrategyType

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