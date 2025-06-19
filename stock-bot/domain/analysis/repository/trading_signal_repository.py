from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

from domain.analysis.models.trading_signal import TradingSignal


class TradingSignalRepository(ABC):
    """거래 신호 저장소 추상 인터페이스"""
    
    @abstractmethod
    def save_signal(self, signal: TradingSignal) -> bool:
        """거래 신호를 저장합니다."""
        pass
    
    @abstractmethod
    def save_signals_bulk(self, signals: List[TradingSignal]) -> bool:
        """여러 거래 신호를 한 번에 저장합니다."""
        pass
    
    @abstractmethod
    def get_signals_by_ticker(self, ticker: str, start_time: datetime, end_time: datetime) -> List[TradingSignal]:
        """특정 종목의 거래 신호를 조회합니다."""
        pass
    
    @abstractmethod
    def get_latest_signals(self, ticker: str, limit: int = 10) -> List[TradingSignal]:
        """최신 거래 신호를 조회합니다."""
        pass
    
    @abstractmethod
    def get_signals_by_type(self, signal_type: str, start_time: datetime, end_time: datetime) -> List[TradingSignal]:
        """특정 타입의 거래 신호를 조회합니다."""
        pass
    
    @abstractmethod
    def delete_old_signals(self, before_time: datetime) -> int:
        """오래된 거래 신호를 삭제합니다."""
        pass 