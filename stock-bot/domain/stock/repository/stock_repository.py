from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import pandas as pd

from domain.stock.models.stock_metadata import StockMetadata
from domain.stock.models.stock_ohlcv import StockOhlcv



class StockRepository(ABC):
    """
    주식 데이터 저장소에 대한 '계약'(추상 인터페이스).
    이 인터페이스는 '무엇을' 할 것인지만 정의하며, '어떻게' 할 것인지는 구현 클래스에 위임합니다.
    """

    @abstractmethod
    def get_metadata_by_ticker(self, ticker: str) -> Optional[StockMetadata]:
        """특정 종목의 메타데이터를 조회합니다."""
        pass

    @abstractmethod
    def save_metadata(self, metadata: StockMetadata) -> None:
        """종목의 메타데이터를 저장하거나 업데이트합니다."""
        pass

    @abstractmethod
    def save_metadata_bulk(self, metadata_list: List[StockMetadata]) -> None:
        """여러 종목의 메타데이터를 한 번에 저장하거나 업데이트합니다."""
        pass
    
    @abstractmethod
    def get_stocks_for_analysis(self) -> List[StockMetadata]:
        """분석 대상 주식 목록을 조회합니다."""
        pass

    @abstractmethod
    def fetch_and_cache_ohlcv(self, tickers: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """
        주어진 종목들의 OHLCV 데이터를 조회하고 캐시합니다.
        
        Args:
            tickers: 조회할 종목 리스트
            days: 조회할 일수
            interval: 데이터 간격 ('1h', '1d' 등)
            
        Returns:
            Dict[str, pd.DataFrame]: 종목별 OHLCV 데이터프레임
        """
        pass
