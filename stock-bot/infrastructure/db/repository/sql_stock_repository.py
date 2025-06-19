from dataclasses import asdict
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
        # 세션을 생성자에 주입하는 대신, 각 메소드에서 get_db() 컨텍스트 매니저를 사용합니다.
        pass

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

        values_to_insert = [asdict(data) for data in metadata_list]
        update_dict = {
            col.name: col for col in mysql_insert(DbStockMetadata).inserted
            if col.name not in ['ticker', 'id']
        }
        stmt = mysql_insert(DbStockMetadata).values(values_to_insert)
        on_duplicate_key_stmt = stmt.on_duplicate_key_update(update_dict)

        try:
            with get_db() as db:
                db.execute(on_duplicate_key_stmt)
                db.commit()
                logger.info(f"Successfully saved {len(metadata_list)} metadata records.")
        except Exception as e:
            logger.error(f"Failed to bulk save metadata: {e}", exc_info=True)
            # Rollback is implicitly handled by the session context manager on error
    
    def get_stocks_for_analysis(self) -> List[DomainStockMetadata]:
        """분석 대상 주식 목록을 조회합니다."""
        try:
            with get_db() as db:
                db_stocks = db.query(DbStockMetadata).filter(
                    DbStockMetadata.need_analysis == True
                ).all()
                
                domain_stocks = []
                for db_stock in db_stocks:
                    domain_stocks.append(DomainStockMetadata(
                        ticker=db_stock.ticker,
                        company_name=db_stock.company_name,
                        exchange=db_stock.exchange,
                        is_active=db_stock.is_active,
                        sector=db_stock.sector,
                        industry=db_stock.industry,
                        quote_type=db_stock.quote_type,
                        currency=db_stock.currency,
                        market_cap=db_stock.market_cap,
                        shares_outstanding=db_stock.shares_outstanding,
                        beta=db_stock.beta,
                        dividend_yield=db_stock.dividend_yield,
                        logo_url=db_stock.logo_url,
                        long_business_summary=db_stock.long_business_summary,
                        need_analysis=db_stock.need_analysis,
                        created_at=db_stock.created_at,
                        updated_at=db_stock.updated_at
                    ))
                
                return domain_stocks
            
        except Exception as e:
            logger.error(f"Error getting stocks for analysis: {e}")
            return [] 