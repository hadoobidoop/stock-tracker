import logging
from time import sleep
from datetime import datetime, timedelta
import pytz
import pandas as pd
from ..utils import get_current_et_time, is_market_open
from ..database_manager import get_stocks_to_analyze, save_intraday_ohlcv
from ..data_collector import  get_existing_intraday_data

import yfinance



logger = logging.getLogger(__name__)

def run_intraday_data_collection_job():
    """장중 1분봉 데이터를 수집하는 작업"""
    try:
        logger.info("Starting intraday data collection job...")
        
        # 현재 시간이 장중인지 확인
        now = datetime.now(pytz.timezone('America/New_York'))
        if not is_market_open(now):
            logger.info("Market is closed. Skipping intraday data collection.")
            return

        # 1분봉 5개를 가져오기 위한 시간 범위 설정
        end_time = now
        start_time = end_time - timedelta(minutes=5)
        
        # 모든 종목의 1분봉 데이터 수집
        for symbol in get_stocks_to_analyze():
            try:
                # 1분봉 5개 데이터 가져오기
                intraday_data = get_existing_intraday_data(symbol, start_time, end_time)
                if intraday_data is not None and not intraday_data.empty:
                    # 기존 데이터와 병합하여 저장
                    existing_data = get_existing_intraday_data(symbol, start_time, end_time)
                    if existing_data is not None and not existing_data.empty:
                        # 기존 데이터와 새로운 데이터 병합
                        merged_data = pd.concat([existing_data, intraday_data])
                        # 중복 제거 (같은 시간의 데이터는 새로운 데이터로 덮어쓰기)
                        merged_data = merged_data[~merged_data.index.duplicated(keep='last')]
                        # 시간순 정렬
                        merged_data = merged_data.sort_index()
                        # 데이터 저장
                        save_intraday_ohlcv(symbol, merged_data)
                        logger.info(f"Successfully updated intraday data for {symbol}")
                    else:
                        # 기존 데이터가 없는 경우 새로운 데이터 저장
                        save_intraday_ohlcv(symbol, intraday_data)
                        logger.info(f"Successfully saved new intraday data for {symbol}")
                else:
                    logger.warning(f"No intraday data available for {symbol}")
            except Exception as e:
                logger.error(f"Error collecting intraday data for {symbol}: {str(e)}")
                continue

        logger.info("Intraday data collection job completed successfully")
    except Exception as e:
        logger.error(f"Error in intraday data collection job: {str(e)}")
        raise

def update_stock_metadata_from_yfinance():
    """[최종 수정본] yfinance를 사용하여 주식 메타데이터를 가져와 DB를 업데이트합니다. (청킹 적용)"""
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
            # yf.Tickers 객체는 여러 티커 정보를 한 번에 요청하는 데 더 효율적입니다.
            tickers_info = yfinance.Tickers(chunk)

            for symbol in chunk:
                # yf.Tickers 객체 내에서 개별 Ticker 객체의 정보에 접근합니다.
                info = tickers_info.tickers[symbol.upper()].info

                if not info or 'symbol' not in info:
                    logger.warning(f"Could not retrieve valid info for {symbol}. Skipping.")
                    continue

                # 데이터 추출 로직은 동일
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

            sleep(1)  # 각 청크 요청 후 지연
        except Exception as e:
            logger.error(f"Failed to process metadata for chunk {i + 1}: {e}")
            continue

    if metadata_to_save:
        update_stock_metadata(metadata_to_save)

    logger.info("JOB END: Stock metadata update process finished.") 