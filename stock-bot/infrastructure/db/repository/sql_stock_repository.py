from dataclasses import asdict
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy import func
import time

from domain.stock.models.stock_metadata import StockMetadata as DomainStockMetadata
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.db_manager import get_db
from infrastructure.db.models import StockMetadata as DbStockMetadata
from infrastructure.db.models.intraday_ohlcv import IntradayOhlcv
from infrastructure.client.yahoo.yahoo_client import get_ohlcv_data
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

        try:
            with get_db() as db:
                table = DbStockMetadata.__table__
                valid_columns = {c.name for c in table.columns}
                
                values_to_insert = []
                for metadata in metadata_list:
                    record = asdict(metadata)
                    filtered_record = {
                        k.lower(): v for k, v in record.items()
                        if k.lower() in valid_columns
                    }
                    values_to_insert.append(filtered_record)

                if not values_to_insert:
                    return

                stmt = mysql_insert(DbStockMetadata).values(values_to_insert)
                
                valid_update_columns = valid_columns - {'id', 'ticker', 'created_at'}
                
                update_dict = {
                    col: stmt.inserted[col]
                    for col in valid_update_columns
                }
                
                on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
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

    def fetch_and_cache_ohlcv(self, tickers: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """
        주어진 종목들의 OHLCV 데이터를 Yahoo Finance에서 조회합니다.
        API 호출량을 최소화하기 위해 한 번에 여러 종목을 조회합니다.
        
        Args:
            tickers: 조회할 종목 리스트
            days: 조회할 일수
            interval: 데이터 간격 ('1h', '1d' 등)
            
        Returns:
            Dict[str, pd.DataFrame]: 종목별 OHLCV 데이터프레임
        """
        try:
            # yfinance의 period 파라미터 형식으로 변환
            period = f"{days+2}d"  # 충분한 데이터를 위해 2일 추가
            
            # 첫 시도
            data_dict, failed_tickers = get_ohlcv_data(tickers, period, interval)
            
            # 실패한 티커에 대해 한 번 더 시도 (API 제한 때문일 수 있음)
            if failed_tickers:
                logger.warning(f"Retrying failed tickers after 2 seconds: {failed_tickers}")
                time.sleep(2)  # API 제한 회피를 위한 대기
                
                # 실패한 티커들만 다시 시도
                retry_data, still_failed = get_ohlcv_data(failed_tickers, period, interval)
                data_dict.update(retry_data)
                
                if still_failed:
                    logger.error(f"Failed to fetch data for tickers even after retry: {still_failed}")
            
            # 요청한 기간에 맞게 데이터 필터링 (UTC 타임존 적용)
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            filtered_dict = {}
            
            for ticker, df in data_dict.items():
                if not df.empty:
                    # 타임스탬프가 UTC가 아니면 UTC로 변환
                    if df.index.tz is None:
                        df.index = df.index.tz_localize('UTC')
                    elif df.index.tz.tzname(None) != 'UTC':  # None은 현재 시점을 의미
                        df.index = df.index.tz_convert('UTC')
                    
                    # 요청한 기간으로 필터링
                    filtered_df = df[df.index >= start_date]
                    if not filtered_df.empty:
                        filtered_dict[ticker] = filtered_df
                    else:
                        logger.warning(f"No data within requested period for {ticker}")
                        filtered_dict[ticker] = pd.DataFrame()
                else:
                    filtered_dict[ticker] = pd.DataFrame()
            
            return filtered_dict
                
        except Exception as e:
            logger.error(f"Error fetching OHLCV data from Yahoo Finance: {e}", exc_info=True)
            return {ticker: pd.DataFrame() for ticker in tickers} 