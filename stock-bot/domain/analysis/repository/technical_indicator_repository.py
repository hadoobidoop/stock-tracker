from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

from domain.analysis.models.technical_indicator import TechnicalIndicator


class TechnicalIndicatorRepository(ABC):
    """기술적 지표 저장소 추상 인터페이스"""
    
    @abstractmethod
    def save_indicators(self, indicators_df: pd.DataFrame, ticker: str, interval: str) -> bool:
        """기술적 지표를 저장합니다."""
        pass
    
    @abstractmethod
    def get_indicators(self, ticker: str, interval: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """특정 기간의 기술적 지표를 조회합니다."""
        pass
    
    @abstractmethod
    def get_latest_indicators(self, ticker: str, interval: str, limit: int = 1) -> pd.DataFrame:
        """최신 기술적 지표를 조회합니다."""
        pass
    
    @abstractmethod
    def delete_old_indicators(self, ticker: str, interval: str, before_time: datetime) -> int:
        """오래된 기술적 지표를 삭제합니다."""
        pass 