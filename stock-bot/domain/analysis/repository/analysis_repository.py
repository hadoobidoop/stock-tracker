from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any

class MarketDataRepository(ABC):
    @abstractmethod
    def get_all_market_data_in_range(self, start_date: datetime, end_date: datetime) -> Dict[datetime, Dict[str, Any]]:
        """
        지정된 기간 내의 모든 일별 시장 지표를 가져옵니다.

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            날짜를 키로, 해당 날짜의 지표 딕셔너리를 값으로 하는 딕셔너리.
            예: {
                datetime.date(2023, 1, 1): {'vix': 20.5, 'buffett_indicator': 1.8},
                datetime.date(2023, 1, 2): {'vix': 21.2, 'buffett_indicator': 1.82}
            }
        """
        pass
