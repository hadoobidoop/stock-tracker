# domain/market_data_backfiller/providers/base_provider.py
from abc import ABC, abstractmethod
from datetime import date

from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class BaseBackfillProvider(ABC):
    """
    모든 시장 데이터 백필 제공자의 기반이 되는 추상 클래스입니다.
    """

    def __init__(self):
        self.repository = SQLMarketDataRepository()

    @abstractmethod
    def backfill(self, start_date: date, end_date: date) -> bool:
        """
        지정된 기간 동안의 데이터를 백필하는 핵심 메서드입니다.
        자식 클래스는 이 메서드를 반드시 구현해야 합니다.

        :param start_date: 백필 시작 날짜
        :param end_date: 백필 종료 날짜
        :return: 백필 성공 여부 (True/False)
        """
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        """Provider의 이름을 반환합니다. 클래스 이��에서 'BackfillProvider'를 떼어냅니다."""
        return self.__class__.__name__.replace("BackfillProvider", "")
