from time import sleep
import yfinance

from domain.stock.config import STOCK_SYMBOLS
from domain.stock.service import update_stock_metadata
from infrastructure.logging import get_logger

logger = get_logger(__name__)

def update_stock_metadata_job():
    """yfinance를 사용하여 주식 메타데이터를 가져와 DB 업데이트를 요청하는 스케줄링 작업입니다."""
    logger.info("JOB START: Updating stock metadata from yfinance...")

    if not STOCK_SYMBOLS:
        logger.warning("STOCK_SYMBOLS list is empty in config.py. Skipping metadata update.")
        return

    chunk_size = 20
    chunks = [STOCK_SYMBOLS[i:i + chunk_size] for i in range(0, len(STOCK_SYMBOLS), chunk_size)]
    metadata_to_save = []

    logger.info(f"Fetching metadata in {len(chunks)} chunks of size {chunk_size}...")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Fetching metadata for chunk {i + 1}/{len(chunks)}...")
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

            sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to process metadata for chunk {i + 1}: {e}", exc_info=True)
            continue

    if metadata_to_save:
        update_stock_metadata(metadata_to_save)

    logger.info("JOB END: Stock metadata update process finished.")

if __name__ == '__main__':
    # 테스트를 위해 직접 실행할 수 있도록 설정
    from infrastructure.logging import setup_logging
    setup_logging()
    update_stock_metadata_job()
