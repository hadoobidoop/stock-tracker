from dataclasses import asdict
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy import func
import time
from sqlalchemy import and_

from domain.stock.models.stock_metadata import StockMetadata as DomainStockMetadata
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.db_manager import get_db
from infrastructure.db.models import StockMetadata as DbStockMetadata
from infrastructure.db.models.intraday_ohlcv import IntradayOhlcv
from infrastructure.client.yahoo.yahoo_client import get_ohlcv_data
from infrastructure.logging import get_logger
from domain.stock.config.settings import OHLCV_COLLECTION

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
        여러 종목의 메타데이터를 배치 처리로 저장하거나 업데이트합니다.
        ticker를 기준으로 UPSERT를 수행하여 각 티커당 하나의 row만 유지합니다.
        배치 크기 50으로 처리하여 메모리 효율성을 확보합니다.
        """
        BATCH_SIZE = 50  # 메타데이터는 OHLCV보다 데이터가 크므로 작은 배치 크기 사용
        
        if not metadata_list:
            logger.info("No metadata to save.")
            return

        try:
            with get_db() as db:
                total_processed = 0
                
                for i in range(0, len(metadata_list), BATCH_SIZE):
                    batch = metadata_list[i:i + BATCH_SIZE]
                    self._execute_metadata_batch_upsert(db, batch)
                    total_processed += len(batch)
                    logger.info(f"Processed metadata batch of {len(batch)} records. Total processed: {total_processed}")
                
                db.commit()
                logger.info(f"Successfully saved/updated total {total_processed} metadata records.")
                
        except Exception as e:
            logger.error(f"Failed to bulk save metadata: {e}", exc_info=True)

    def _execute_metadata_batch_upsert(self, db: Session, metadata_batch: List[DomainStockMetadata]) -> None:
        """
        메타데이터 배치를 벌크 업서트로 처리합니다.
        ticker를 기준으로 UPSERT를 수행합니다.
        
        Args:
            db: 데이터베이스 세션
            metadata_batch: 업서트할 메타데이터 배치 리스트
        """
        try:
            values_to_insert = []
            for metadata in metadata_batch:
                values_to_insert.append(asdict(metadata))

            # 유효한 컬럼만 필터링 (SQL 인젝션 방지 및 스키마 검증)
            valid_columns = {c.name for c in DbStockMetadata.__table__.columns}
            
            filtered_values = []
            for values in values_to_insert:
                filtered_values.append({k: v for k, v in values.items() if k in valid_columns})

            if not filtered_values:
                logger.warning("No valid metadata columns found after filtering.")
                return

            # MySQL UPSERT 구문 생성
            stmt = mysql_insert(DbStockMetadata).values(filtered_values)
            
            # 업데이트할 컬럼 정의 (ticker와 created_at 제외)
            update_dict = {
                'company_name': stmt.inserted.company_name,
                'exchange': stmt.inserted.exchange,
                'sector': stmt.inserted.sector,
                'industry': stmt.inserted.industry,
                'is_active': stmt.inserted.is_active,
                'quote_type': stmt.inserted.quote_type,
                'currency': stmt.inserted.currency,
                'market_cap': stmt.inserted.market_cap,
                'shares_outstanding': stmt.inserted.shares_outstanding,
                'beta': stmt.inserted.beta,
                'dividend_yield': stmt.inserted.dividend_yield,
                'logo_url': stmt.inserted.logo_url,
                'long_business_summary': stmt.inserted.long_business_summary,
                'need_analysis': stmt.inserted.need_analysis,
                'updated_at': stmt.inserted.updated_at
            }
            
            # UPSERT 실행 (ticker를 기준으로)
            on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
            db.execute(on_duplicate_key_stmt)
            
        except Exception as e:
            logger.error(f"Error during metadata bulk upsert: {e}", exc_info=True)
            raise

    def count_stocks_for_analysis(self) -> int:
        """분석 대상 주식의 총 개수를 반환합니다."""
        try:
            with get_db() as db:
                return db.query(DbStockMetadata).filter(DbStockMetadata.need_analysis == True).count()
        except Exception as e:
            logger.error(f"Error counting stocks for analysis: {e}", exc_info=True)
            return 0

    def get_stocks_for_analysis(self, page: int = 1, page_size: int = 100) -> List[DomainStockMetadata]:
        """분석 대상 주식 목록을 페이징하여 조회합니다. 중복된 티커는 제거됩니다."""
        try:
            with get_db() as db:
                # 서브쿼리를 사용하여 각 티커별 가장 최근 레코드만 선택
                latest_records = db.query(
                    DbStockMetadata.ticker,
                    func.max(DbStockMetadata.updated_at).label('max_updated_at')
                ).filter(
                    DbStockMetadata.need_analysis == True
                ).group_by(
                    DbStockMetadata.ticker
                ).subquery()
                
                # 메인 쿼리에서 서브쿼리 결과와 조인
                db_stocks = db.query(DbStockMetadata).join(
                    latest_records,
                    and_(
                        DbStockMetadata.ticker == latest_records.c.ticker,
                        DbStockMetadata.updated_at == latest_records.c.max_updated_at
                    )
                ).order_by(
                    DbStockMetadata.ticker
                ).offset(
                    (page - 1) * page_size
                ).limit(page_size).all()
                
                domain_stocks = []
                seen_tickers = set()  # 추가 안전장치로 중복 체크
                
                for db_stock in db_stocks:
                    if db_stock.ticker not in seen_tickers:  # 중복 체크
                        seen_tickers.add(db_stock.ticker)
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

    def save_ohlcv_data(self, ohlcv_data: Dict[str, pd.DataFrame], interval: str) -> bool:
        """
        OHLCV 데이터를 데이터베이스에 저장하거나 업데이트합니다 (UPSERT).
        기존 데이터가 있으면 업데이트하고, 없으면 새로 생성합니다.
        배치 크기 300으로 대량의 데이터를 효율적으로 처리합니다.
        
        Args:
            ohlcv_data: 종목별 OHLCV 데이터 딕셔너리 {'ticker': DataFrame}
            interval: 데이터 간격 ('1d', '1h', '5m' 등)
            
        Returns:
            bool: 저장 성공 여부
        """
        BATCH_SIZE = 300  # 한 번에 처리할 레코드 수
        
        if not ohlcv_data:
            logger.info(f"No {interval} OHLCV data to save.")
            return True

        try:
            with get_db() as db:
                records_to_save = []
                total_processed = 0
                
                for ticker, df in ohlcv_data.items():
                    if df.empty:
                        logger.warning(f"Empty data for ticker {ticker}, skipping.")
                        continue
                    
                    for timestamp, row in df.iterrows():
                        record = {
                            'timestamp_utc': timestamp,
                            'ticker': ticker.upper(),
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': int(row['Volume']),
                            'interval': interval
                        }
                        records_to_save.append(record)
                        
                        # 배치 크기에 도달하면 처리
                        if len(records_to_save) >= BATCH_SIZE:
                            self._execute_bulk_upsert(db, records_to_save)
                            total_processed += len(records_to_save)
                            logger.info(f"Processed batch of {len(records_to_save)} records. Total processed: {total_processed}")
                            records_to_save = []
                
                # 남은 레코드 처리
                if records_to_save:
                    self._execute_bulk_upsert(db, records_to_save)
                    total_processed += len(records_to_save)
                    logger.info(f"Processed final batch of {len(records_to_save)} records. Total processed: {total_processed}")
                
                db.commit()
                logger.info(f"Successfully saved/updated total {total_processed} {interval} OHLCV records.")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save {interval} OHLCV data: {e}", exc_info=True)
            return False

    def _execute_bulk_upsert(self, db: Session, records: List[Dict]) -> None:
        """
        주어진 레코드들을 벌크 업서트로 처리합니다.
        
        Args:
            db: 데이터베이스 세션
            records: 업서트할 레코드 리스트
        """
        try:
            # MySQL UPSERT 구문 생성
            stmt = mysql_insert(IntradayOhlcv).values(records)
            
            # 업데이트할 컬럼들 정의 (기본키 제외)
            update_dict = {
                'open': stmt.inserted.open,
                'high': stmt.inserted.high,
                'low': stmt.inserted.low,
                'close': stmt.inserted.close,
                'volume': stmt.inserted.volume,
                'interval': stmt.inserted.interval
            }
            
            # UPSERT 실행
            on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
            db.execute(on_duplicate_key_stmt)
            
        except Exception as e:
            logger.error(f"Error during bulk upsert: {e}", exc_info=True)
            raise

    def save_daily_ohlcv(self, ohlcv_data: Dict[str, pd.DataFrame]) -> bool:
        """
        일봉 OHLCV 데이터를 저장합니다. (하위 호환성을 위한 래퍼 메서드)
        """
        return self.save_ohlcv_data(ohlcv_data, '1d')

    def fetch_ohlcv_data_from_yahoo(self, tickers: List[str], period: str, interval: str) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        try:
            # 첫 시도
            data_dict, failed_tickers = get_ohlcv_data(tickers, period, interval)
            
            # 실패한 티커에 대해 재시도
            if failed_tickers:
                logger.warning(f"Retrying failed tickers after {OHLCV_COLLECTION['RETRY']['WAIT_SECONDS']} seconds: {failed_tickers}")
                time.sleep(OHLCV_COLLECTION['RETRY']['WAIT_SECONDS'])
                
                # 실패한 티커들만 다시 시도
                retry_data, still_failed = get_ohlcv_data(failed_tickers, period, interval)
                data_dict.update(retry_data)
                
                if still_failed:
                    logger.error(f"Failed to fetch data for tickers even after retry: {still_failed}")
                
                return data_dict, still_failed
            
            return data_dict, failed_tickers
                
        except Exception as e:
            logger.error(f"Error fetching OHLCV data from Yahoo Finance: {e}", exc_info=True)
            return {}, tickers

    def get_ohlcv_data_from_db(self, tickers: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """
        데이터베이스에서 OHLCV 데이터를 조회합니다.
        지정된 기간 동안의 데이터를 조회하며, 데이터가 부족할 경우 빈 딕셔너리를 반환합니다.
        
        Args:
            tickers: 조회할 종목 리스트
            days: 조회할 일수
            interval: 데이터 간격 ('1d', '1h', '5m' 등)
            
        Returns:
            Dict[str, pd.DataFrame]: 종목별 OHLCV 데이터
        """
        if not tickers:
            return {}
            
        try:
            # 조회 시작 날짜 계산 (현재 시간에서 지정된 일수만큼 뺀 날짜)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            result = {}
            
            with get_db() as db:
                for ticker in tickers:
                    # 각 종목별로 데이터 조회
                    query = db.query(IntradayOhlcv).filter(
                        IntradayOhlcv.ticker == ticker,
                        IntradayOhlcv.interval == interval,
                        IntradayOhlcv.timestamp_utc >= start_time,
                        IntradayOhlcv.timestamp_utc <= end_time
                    ).order_by(IntradayOhlcv.timestamp_utc)
                    
                    records = query.all()
                    
                    if records:
                        # DataFrame으로 변환
                        data = []
                        for record in records:
                            data.append({
                                'Open': record.open,
                                'High': record.high,
                                'Low': record.low,
                                'Close': record.close,
                                'Volume': record.volume
                            })
                        
                        df = pd.DataFrame(data)
                        df.index = [record.timestamp_utc for record in records]
                        df.index = pd.to_datetime(df.index, utc=True)
                        result[ticker] = df
                    else:
                        logger.warning(f"No data found for ticker {ticker} with interval {interval}")
                        result[ticker] = pd.DataFrame()
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting OHLCV data from DB: {e}", exc_info=True)
            return {}

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
        if not tickers:
            return {}
            
        try:
            logger.info(f"Smart fetching OHLCV data for {len(tickers)} tickers with {days} days lookback")
            
            # 1. 먼저 DB에서 데이터 확인
            db_data = self.get_ohlcv_data_from_db(tickers, days, interval)
            
            # 2. 데이터가 충분한 티커와 부족한 티커 분류
            sufficient_tickers = []
            insufficient_tickers = []
            
            min_required_points = self._calculate_min_data_points(days, interval)
            
            for ticker in tickers:
                if ticker in db_data and not db_data[ticker].empty:
                    if len(db_data[ticker]) >= min_required_points:
                        sufficient_tickers.append(ticker)
                        logger.info(f"Using cached data for {ticker}: {len(db_data[ticker])} data points")
                    else:
                        insufficient_tickers.append(ticker)
                        logger.info(f"Insufficient cached data for {ticker}: {len(db_data[ticker])} < {min_required_points}")
                else:
                    insufficient_tickers.append(ticker)
                    logger.info(f"No cached data found for {ticker}")
            
            result = {}
            
            # 3. 충분한 데이터가 있는 티커는 DB에서 사용
            for ticker in sufficient_tickers:
                result[ticker] = db_data[ticker]
            
            # 4. 부족한 데이터만 Yahoo API에서 가져오기
            if insufficient_tickers:
                logger.info(f"Fetching from Yahoo API for {len(insufficient_tickers)} tickers: {insufficient_tickers}")
                
                # 조회할 기간 설정 (days를 기반으로 period 계산)
                if days <= 7:
                    period = "7d"
                elif days <= 30:
                    period = "1mo"
                elif days <= 90:
                    period = "3mo"
                elif days <= 180:
                    period = "6mo"
                elif days <= 365:
                    period = "1y"
                elif days <= 730:
                    period = "2y"
                else:
                    period = "5y"
                
                # Yahoo Finance에서 데이터 가져오기 (API 호출 제한 적용)
                fetched_data, failed_tickers = self._fetch_with_rate_limit(insufficient_tickers, period, interval)
                
                if failed_tickers:
                    logger.warning(f"Failed to fetch data for tickers: {failed_tickers}")
                
                # 가져온 데이터를 데이터베이스에 저장
                if fetched_data:
                    success = self.save_ohlcv_data(fetched_data, interval)
                    if success:
                        logger.info(f"Successfully cached OHLCV data for {len(fetched_data)} tickers")
                    else:
                        logger.warning("Some errors occurred while caching OHLCV data")
                
                # 결과에 추가
                result.update(fetched_data)
            
            logger.info(f"Successfully retrieved data for {len(result)} out of {len(tickers)} tickers")
            return result
            
        except Exception as e:
            logger.error(f"Error in fetch_and_cache_ohlcv: {e}", exc_info=True)
            return {}

    def _calculate_min_data_points(self, days: int, interval: str) -> int:
        """필요한 최소 데이터 포인트 수를 계산합니다."""
        if interval == '1d':
            # 일봉의 경우 주말을 고려하여 요청 일수의 70% 정도면 충분
            return max(int(days * 0.7), 30)  # 최소 30일
        elif interval == '1h':
            # 시간봉의 경우 주말과 비시장시간을 고려
            # 하루에 약 6.5시간 거래 (미국 시장 기준)
            return max(int(days * 6.5 * 0.7), 48)  # 최소 48시간
        else:
            # 기타 간격의 경우 보수적으로 계산
            return max(int(days * 0.5), 20)

    def _fetch_with_rate_limit(self, tickers: List[str], period: str, interval: str) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        """API 호출 제한을 적용하여 데이터를 가져옵니다."""
        try:
            # 페이지 크기에 따라 분할하여 호출
            page_size = OHLCV_COLLECTION['API_CONTROL']['PAGE_SIZE']
            rate_limit_delay = OHLCV_COLLECTION['API_CONTROL']['RATE_LIMIT_DELAY_SECONDS']
            
            all_data = {}
            all_failed = []
            
            for i in range(0, len(tickers), page_size):
                batch_tickers = tickers[i:i + page_size]
                logger.info(f"Fetching batch {i//page_size + 1}: {batch_tickers}")
                
                # 배치별로 데이터 가져오기
                batch_data, batch_failed = self.fetch_ohlcv_data_from_yahoo(batch_tickers, period, interval)
                
                all_data.update(batch_data)
                all_failed.extend(batch_failed)
                
                # 마지막 배치가 아니면 대기
                if i + page_size < len(tickers):
                    logger.info(f"Rate limiting: waiting {rate_limit_delay} seconds before next batch...")
                    import time
                    time.sleep(rate_limit_delay)
            
            return all_data, all_failed
            
        except Exception as e:
            logger.error(f"Error in rate limited fetch: {e}", exc_info=True)
            return {}, tickers 