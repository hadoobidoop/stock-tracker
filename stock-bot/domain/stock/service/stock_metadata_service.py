from typing import List, Dict, Any

from domain.stock.models.stock_metadata import StockMetadata
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)

def update_stock_metadata(metadata_dicts: List[Dict[str, Any]]):
    """
    딕셔너리 리스트 형태의 메타데이터를 받아 도메인 모델로 변환한 후,
    Repository를 통해 데이터베이스에 저장(UPSERT)합니다.
    """
    if not metadata_dicts:
        logger.warning("Received an empty list of metadata. No action taken.")
        return

    # 딕셔너리를 StockMetadata 도메인 모델 객체 리스트로 변환
    # dataclasses는 딕셔너리에 없는 키는 무시하므로 안전합니다.
    metadata_models = [StockMetadata(**data) for data in metadata_dicts]

    try:
        # Repository를 인스턴스화하고 대량 저장 메소드를 호출합니다.
        repo = SQLStockRepository()
        repo.save_metadata_bulk(metadata_models)
        logger.info(f"Successfully triggered bulk save for {len(metadata_models)} metadata items.")
    except Exception as e:
        logger.error(f"Failed to initialize repository or save metadata: {e}", exc_info=True) 