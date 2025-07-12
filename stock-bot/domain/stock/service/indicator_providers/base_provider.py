from abc import ABC, abstractmethod

from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository


class BaseIndicatorProvider(ABC):
    """
    모든 시장 지표 제공자의 기반이 되는 추상 클래스입니다.
    """

    def __init__(self):
        self.repository = SQLMarketDataRepository()

    @abstractmethod
    def update(self) -> bool:
        """
        지표 데이터를 업데이트하는 핵심 메서드입니다.
        자식 클래스는 이 메서드를 반드시 구현해야 합니다.

        :return: 업데이트 성공 여부 (True/False)
        """
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        """Provider의 이름을 반환합니다. 클래스 이름에서 'Provider'를 떼어냅니다."""
        return self.__class__.__name__.replace("Provider", "")
