"""
전략 기본 추상 클래스 - 모든 전략이 상속받는 핵심 인터페이스
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from domain.signals.models.enums import StrategyType
from domain.strategies.strategy_config import StrategyConfig
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BaseStrategy(ABC):
    """모든 전략이 상속받는 기본 추상 클래스"""

    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        self.strategy_type = strategy_type
        self.config = config
        self.is_initialized = False
        
        # 기본 성능 추적 변수들 (PerformanceMixin에서 확장됨)
        self.last_analysis_time: Optional[datetime] = None

    @abstractmethod
    def initialize(self) -> bool:
        """
        전략에 필요한 리소스(예: SignalOrchestrator)를 초기화합니다.
        각 구체적인 전략 클래스에서 구현해야 합니다.
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

    def can_generate_signal(self, current_time: datetime) -> bool:
        """현재 신호를 생성할 수 있는지 확인 (쿨다운 체크)"""
        if self.last_analysis_time is None:
            return True

        # 최소 간격 체크 (예: 5분)
        min_interval_minutes = 5
        time_diff = current_time - self.last_analysis_time
        return time_diff.total_seconds() >= min_interval_minutes * 60