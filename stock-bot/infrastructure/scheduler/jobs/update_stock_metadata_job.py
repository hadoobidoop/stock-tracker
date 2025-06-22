from time import sleep
import yfinance
import math

from domain.stock.config import STOCK_SYMBOLS
from domain.stock.service import update_stock_metadata
from infrastructure.logging import get_logger
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository

logger = get_logger(__name__)

def _fetch_and_save_metadata(tickers: list):
    """주어진 티커 목록에 대한 메타데이터를 가져와 저장합니다."""
    if not tickers:
        return
        
    chunk_size = 20
    metadata_to_save = []
    
    logger.info(f"Fetching metadata for {len(tickers)} tickers in chunks of {chunk_size}...")
    
    total_chunks = math.ceil(len(tickers) / chunk_size)
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        chunk_num = i//chunk_size + 1
        logger.info(f"Fetching metadata for chunk {chunk_num}/{total_chunks} (tickers: {chunk})...")
        
        try:
            tickers_info = yfinance.Tickers(chunk)
            for symbol in chunk:
                info = tickers_info.tickers[symbol.upper()].info
                if not info or 'symbol' not in info:
                    logger.warning(f"Could not retrieve valid info for {symbol}. Skipping.")
                    continue

                metadata = {
                    'ticker': info.get('symbol'),
                    'company_name': info.get('longName'),
                    'exchange': info.get('exchange'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'is_active': not info.get('isDelisted', False),
                    'quote_type': info.get('quoteType'),
                    'currency': info.get('currency'),
                    'market_cap': info.get('marketCap'),
                    'shares_outstanding': info.get('sharesOutstanding'),
                    'beta': info.get('beta'),
                    'dividend_yield': info.get('dividendYield'),
                    'logo_url': info.get('logo_url'),
                    'long_business_summary': info.get('longBusinessSummary')
                }
                metadata_to_save.append(metadata)

            # API 호출 제한을 위해 30초 대기 (마지막 청크가 아닌 경우만)
            if chunk_num < total_chunks:
                logger.info(f"Waiting 30 seconds before next API call to avoid rate limiting...")
                sleep(30)
                
        except Exception as e:
            logger.error(f"Failed to process metadata for chunk {chunk_num}: {e}", exc_info=True)
            continue

    if metadata_to_save:
        logger.info(f"Saving {len(metadata_to_save)} metadata records to database...")
        update_stock_metadata(metadata_to_save)


def update_stock_metadata_job():
    """
    주식 메타데이터를 업데이트합니다.
    1. DB에 저장된 모든 종목의 메타데이터를 업데이트합니다.
    2. STOCK_SYMBOLS 설정에 있으나 DB에 없는 신규 종목을 추가합니다.
    """
    logger.info("JOB START: Updating stock metadata from yfinance...")
    
    repository = SQLStockRepository()
    page_size = 100
    all_db_tickers = set()  # 중복 제거를 위해 set 사용

    # 1. DB에 있는 모든 종목의 메타데이터 업데이트
    logger.info("Step 1: Updating metadata for existing stocks in DB...")
    total_stocks = repository.count_stocks_for_analysis()
    
    if total_stocks > 0:
        total_pages = math.ceil(total_stocks / page_size)
        logger.info(f"Found {total_stocks} stocks in DB. Updating in {total_pages} pages...")
        
        for page in range(1, total_pages + 1):
            logger.info(f"Processing page {page}/{total_pages}...")
            stocks = repository.get_stocks_for_analysis(page=page, page_size=page_size)
            # set으로 변환하여 중복 제거
            current_tickers = {stock.ticker for stock in stocks}
            all_db_tickers.update(current_tickers)
            
            if current_tickers:  # set이 비어있지 않은 경우에만 처리
                logger.info(f"Processing unique tickers: {sorted(current_tickers)}")
                _fetch_and_save_metadata(list(current_tickers))
    else:
        logger.info("No existing stocks for analysis found in DB.")

    # 2. STOCK_SYMBOLS에만 있는 신규 종목 추가
    logger.info("Step 2: Checking for new symbols from STOCK_SYMBOLS config...")
    if not STOCK_SYMBOLS:
        logger.info("STOCK_SYMBOLS list is empty. No new symbols to add.")
    else:
        config_tickers_set = set(STOCK_SYMBOLS)
        
        # set 연산으로 새로운 티커 찾기
        new_tickers = config_tickers_set - all_db_tickers
        
        if new_tickers:
            logger.info(f"Found {len(new_tickers)} new tickers to add from STOCK_SYMBOLS: {sorted(new_tickers)}")
            _fetch_and_save_metadata(list(new_tickers))
        else:
            logger.info("No new tickers to add from STOCK_SYMBOLS. DB is up to date with config.")

    logger.info("JOB END: Stock metadata update process finished.")

if __name__ == '__main__':
    # 테스트를 위해 직접 실행할 수 있도록 설정
    from infrastructure.logging import setup_logging
    setup_logging()
    update_stock_metadata_job()
