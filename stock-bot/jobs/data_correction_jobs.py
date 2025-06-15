import logging
from datetime import timedelta, datetime, timezone
from time import sleep


from ..config import INTRADAY_INTERVAL
from ..data_collector import get_ohlcv_data
from ..database_manager import save_intraday_ohlcv, get_stocks_to_analyze, get_db
from ..database_setup import IntradayOhlcv
from ..utils import get_current_et_time, is_market_open

logger = logging.getLogger(__name__)

def run_intraday_data_correction_job():
    """장 마감 후 해당 거래일의 1분봉 데이터를 보정하는 배치 작업"""
    logger.info("JOB START: Intraday OHLCV data correction job...")
    
    current_et = get_current_et_time()
    
    # 장이 열려있는 경우 실행하지 않음
    if is_market_open():
        logger.info("Market is still open. Skipping correction job.")
        return
        
    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # 오늘 거래일의 시작 시간과 종료 시간 계산
    market_open_time = current_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close_time = current_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    logger.info(f"Correcting intraday data for trading day: {market_open_time.date()}")
    logger.info(f"Time range: {market_open_time} to {market_close_time}")

    # DB 세션 생성
    db = next(get_db())
    try:
        # 1. 먼저 해당 기간의 기존 데이터 삭제
        deleted_count = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.timestamp_utc.between(market_open_time, market_close_time)
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Deleted {deleted_count} existing records for the trading day")

        # 청크 단위로 데이터 수집 (API 호출 최적화)
        chunk_size = 20
        chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {i + 1}/{len(chunks)}...")
                
                # 오늘 하루치 데이터만 가져오기 위해 period를 '1d'로 설정
                chunk_data = get_ohlcv_data(chunk, "1d", INTRADAY_INTERVAL)
                
                if not chunk_data:
                    logger.warning(f"No data received for chunk {i + 1}")
                    continue
                    
                for symbol, df_ohlcv in chunk_data.items():
                    if not df_ohlcv.empty:
                        # 거래 시간 범위에 해당하는 데이터만 필터링
                        mask = (df_ohlcv.index >= market_open_time) & (df_ohlcv.index <= market_close_time)
                        df_filtered = df_ohlcv[mask]
                        
                        if not df_filtered.empty:
                            save_intraday_ohlcv(df_filtered, symbol, interval=INTRADAY_INTERVAL)
                            logger.info(f"Saved {len(df_filtered)} rows of {INTRADAY_INTERVAL} data for {symbol}")
                        else:
                            logger.warning(f"No data within market hours for {symbol}")
                    else:
                        logger.warning(f"Empty DataFrame received for {symbol}")
                        
                sleep(1)  # API 호출 간 딜레이
                
            except Exception as e:
                logger.error(f"Error processing chunk {i + 1}: {e}")
                db.rollback()  # 에러 발생 시 롤백
                continue
                
    except Exception as e:
        logger.error(f"Error during data correction: {e}")
        db.rollback()
    finally:
        db.close()
            
    logger.info("JOB END: Intraday OHLCV data correction job completed.")

def run_daily_ohlcv_correction_job():
    """매일 최근 한 달치의 일봉 데이터를 수집하고 보정하는 배치 작업"""
    logger.info("JOB START: Daily OHLCV data correction job...")
    
    current_et = get_current_et_time()
    stocks_to_analyze = get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # 데이터 수집 기간 설정 (오늘 포함 최근 30일)
    end_date = current_et
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"Collecting daily data from {start_date.date()} to {end_date.date()}")

    # DB 세션 생성
    db = next(get_db())
    try:
        # 1. 해당 기간의 기존 데이터 삭제
        deleted_count = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.timestamp_utc.between(start_date, end_date),
            IntradayOhlcv.interval == '1d'  # 일봉 데이터만 삭제
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Deleted {deleted_count} existing daily records")

        # 청크 단위로 데이터 수집 (API 호출 최적화)
        chunk_size = 20
        chunks = [stocks_to_analyze[i:i + chunk_size] for i in range(0, len(stocks_to_analyze), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {i + 1}/{len(chunks)}...")
                
                # 일봉 데이터 수집
                chunk_data = get_ohlcv_data(chunk, "30d", '1d')
                
                if not chunk_data:
                    logger.warning(f"No data received for chunk {i + 1}")
                    continue
                    
                for symbol, df_daily in chunk_data.items():
                    if not df_daily.empty:
                        # 거래일만 필터링 (주말 제외)
                        df_daily = df_daily[df_daily.index.dayofweek < 5]  # 0-4: 월-금
                        
                        if not df_daily.empty:
                            save_intraday_ohlcv(df_daily, symbol, interval='1d')
                            logger.info(f"Saved {len(df_daily)} rows of daily data for {symbol}")
                        else:
                            logger.warning(f"No trading day data for {symbol}")
                    else:
                        logger.warning(f"Empty DataFrame received for {symbol}")
                        
                sleep(1)  # API 호출 간 딜레이
                
            except Exception as e:
                logger.error(f"Error processing chunk {i + 1}: {e}")
                db.rollback()  # 에러 발생 시 롤백
                continue
                
    except Exception as e:
        logger.error(f"Error during daily data correction: {e}")
        db.rollback()
    finally:
        db.close()
            
    logger.info("JOB END: Daily OHLCV data correction job completed.") 