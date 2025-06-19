from abc import ABC, abstractmethod
from typing import List, Optional

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
