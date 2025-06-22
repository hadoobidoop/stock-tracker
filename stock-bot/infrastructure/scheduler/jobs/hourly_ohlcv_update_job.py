from datetime import datetime, timedelta
import pandas as pd
import math
import time

from infrastructure.logging import get_logger
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from domain.stock.config.settings import OHLCV_COLLECTION

logger = get_logger(__name__)

def hourly_ohlcv_update_job():
    """
    야후 파이낸스에서 1시간봉 데이터를 가져와 DB에 저장하는 스케줄링 작업입니다.
    DB에 저장된 모든 분석 대상 종목에 대해 페이징 처리하여 실행합니다.
    """
    logger.info("JOB START: Hourly OHLCV data update from Yahoo Finance...")

    repository = SQLStockRepository()
    
    # 분석 대상 주식 수 확인
    total_stocks = repository.count_stocks_for_analysis()
    if total_stocks == 0:
        logger.warning("No stocks to analyze in the database. Skipping job.")
        return

    # 설정에서 파라미터 가져오기
    hourly_settings = OHLCV_COLLECTION["HOURLY"]
    api_control_settings = OHLCV_COLLECTION["API_CONTROL"]
    period = hourly_settings["PERIOD"]
    interval = hourly_settings["INTERVAL"]
    days_to_keep = hourly_settings["DAYS_TO_KEEP"]
    
    page_size = api_control_settings["PAGE_SIZE"]
    rate_limit_delay = api_control_settings["RATE_LIMIT_DELAY_SECONDS"]
    total_pages = math.ceil(total_stocks / page_size)
    
    logger.info(f"Starting hourly OHLCV update for {total_stocks} stocks in {total_pages} pages...")

    for page in range(1, total_pages + 1):
        logger.info(f"Processing page {page}/{total_pages}...")
        
        try:
            stocks = repository.get_stocks_for_analysis(page=page, page_size=page_size)
            symbols = [stock.ticker for stock in stocks]

            if not symbols:
                logger.warning(f"No symbols found for page {page}. Skipping.")
                continue

            # Yahoo Finance에서 데이터 조회
            successful_data, failed_tickers = repository.fetch_ohlcv_data_from_yahoo(
                tickers=symbols,
                period=period,
                interval=interval
            )
            
            if failed_tickers:
                logger.warning(f"Failed to fetch hourly data for tickers: {failed_tickers}")
            
            if not successful_data:
                logger.error("No hourly data retrieved from Yahoo Finance for this page.")
                continue
            
            # 데이터 검증 및 정리
            validated_data = {}
            for ticker, df in successful_data.items():
                if df.empty:
                    logger.warning(f"Empty hourly data received for {ticker}")
                    continue
                
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in df.columns for col in required_columns):
                    logger.error(f"Missing required columns for {ticker}. Available: {df.columns.tolist()}")
                    continue
                
                df_clean = df.dropna()
                if df_clean.empty:
                    logger.warning(f"No valid hourly data for {ticker} after cleaning")
                    continue
                
                days_ago = datetime.now() - timedelta(days=days_to_keep)
                if df_clean.index.tz is None:
                    df_clean.index = df_clean.index.tz_localize('UTC')
                else:
                    df_clean.index = df_clean.index.tz_convert('UTC')
                
                days_ago_utc = days_ago.replace(tzinfo=df_clean.index.tz)
                df_filtered = df_clean[df_clean.index >= days_ago_utc]
                
                if not df_filtered.empty:
                    validated_data[ticker] = df_filtered
                    logger.info(f"Prepared {len(df_filtered)} hourly records for {ticker}")
            
            if not validated_data:
                logger.error("No valid hourly data to save after validation for this page.")
                continue
            
            # 데이터베이스에 저장
            save_success = repository.save_ohlcv_data(validated_data, interval=interval)
            
            if save_success:
                total_records = sum(len(df) for df in validated_data.values())
                logger.info(f"Page {page}/{total_pages}: Successfully saved/updated {total_records} hourly OHLCV records.")
            else:
                logger.error(f"Page {page}/{total_pages}: Failed to save hourly OHLCV data.")
                
            # 최신 시점의 지표만 저장
            for ticker, df in validated_data.items():
                latest_indicators = df.iloc[-1:].copy()  # 마지막 행만
                repository.save_indicators(latest_indicators, ticker, '1h')
                
        except Exception as e:
            logger.error(f"An unexpected error occurred on page {page}: {e}", exc_info=True)
        
        # 마지막 페이지가 아니면 API 호출 제한을 위해 대기
        if page < total_pages:
            logger.info(f"Waiting for {rate_limit_delay} seconds before next page...")
            time.sleep(rate_limit_delay)
    
    logger.info("JOB END: Hourly OHLCV data update process finished.")

if __name__ == '__main__':
    from infrastructure.logging import setup_logging
    setup_logging()
    hourly_ohlcv_update_job() 