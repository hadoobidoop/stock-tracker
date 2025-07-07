from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
import pandas as pd

from domain.stock.models.stock_metadata import StockMetadata



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
    def count_stocks_for_analysis(self) -> int:
        pass

    @abstractmethod
    def get_stocks_for_analysis(self, page: int, page_size: int) -> List[StockMetadata]:
        """분석 대상 주식 목록을 조회합니다."""
        pass

    @abstractmethod
    def save_ohlcv_data(self, ohlcv_data: Dict[str, pd.DataFrame], interval: str) -> bool:
        """
        OHLCV 데이터를 저장하거나 업데이트합니다.
        
        Args:
            ohlcv_data: 종목별 OHLCV 데이터 딕셔너리 {'ticker': DataFrame}
            interval: 데이터 간격 ('1d', '1h', '5m' 등)
            
        Returns:
            bool: 저장 성공 여부
        """
        pass

    @abstractmethod
    def fetch_ohlcv_data_from_yahoo(self, tickers: List[str], period: str, interval: str) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        pass

    @abstractmethod
    def get_ohlcv_data_from_db(self, tickers: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        pass

    @abstractmethod
    def fetch_and_cache_ohlcv(self, tickers: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """
        Yahoo Finance에서 OHLCV 데이터를 가져와서 데이터베이스에 캐시하고 반환합니다.
        백테스팅 엔진에서 사용하는 메서드입니다.
        
        Args:
            tickers: 조회할 종목 리스트
            days: 조회할 일수 
            interval: 데이터 간격 ('1d', '1h', '5m' 등)
            
        Returns:
            Dict[str, pd.DataFrame]: 종목별 OHLCV 데이터
        """
        pass
