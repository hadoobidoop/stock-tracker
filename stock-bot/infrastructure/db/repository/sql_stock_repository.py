from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert as mysql_insert

from domain.stock.models.stock_metadata import StockMetadata as DomainStockMetadata
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.db_manager import get_db
from infrastructure.db.models import StockMetadata as DbStockMetadata
from infrastructure.logging import get_logger

logger = get_logger(__name__)

class SQLStockRepository(StockRepository):
    """StockRepository의 SQLAlchemy 구현체입니다."""

    def __init__(self):
        # get_db는 제너레이터이므로, next()를 사용하여 세션을 얻습니다.
        self.db: Session = next(get_db())

    def get_metadata_by_ticker(self, ticker: str) -> Optional[DomainStockMetadata]:
        # 구현은 생략합니다 (필요시 추가).
        raise NotImplementedError

    def save_metadata(self, metadata: DomainStockMetadata) -> None:
        # 구현은 생략합니다 (필요시 추가).
        raise NotImplementedError

    def save_metadata_bulk(self, metadata_list: List[DomainStockMetadata]) -> None:
        """
        여러 주식 메타데이터를 데이터베이스에 한 번에 저장하거나 업데이트합니다 (UPSERT).
        MySQL의 INSERT ... ON DUPLICATE KEY UPDATE 문을 사용하여 효율적으로 처리합니다.
        """
        if not metadata_list:
            logger.info("No metadata to save.")
            return

        # 도메인 모델 리스트를 DB 모델 딕셔너리 리스트로 변환합니다.
        values_to_insert = [data.dict() for data in metadata_list]

        # ON DUPLICATE KEY UPDATE를 위한 딕셔너리를 만듭니다.
        # ticker를 제외한 모든 필드를 업데이트 대상으로 지정합니다.
        update_dict = {
            col.name: col for col in mysql_insert(DbStockMetadata).inserted
            if col.name != 'ticker' and col.name != 'id'
        }

        # SQLAlchemy Core의 insert 문을 사용합니다.
        stmt = mysql_insert(DbStockMetadata).values(values_to_insert)

        # ON DUPLICATE KEY UPDATE 절을 구성합니다.
        on_duplicate_key_stmt = stmt.on_duplicate_key_update(update_dict)

        try:
            self.db.execute(on_duplicate_key_stmt)
            self.db.commit()
            logger.info(f"Successfully saved {len(metadata_list)} metadata records.")
        except Exception as e:
            logger.error(f"Failed to bulk save metadata: {e}", exc_info=True)
            self.db.rollback()
        finally:
            self.db.close() 