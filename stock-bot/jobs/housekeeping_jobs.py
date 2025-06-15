import logging
from datetime import timedelta, datetime, timezone

from ..config import DATA_RETENTION_DAYS
from ..database_manager import get_db
from ..database_setup import IntradayOhlcv, TechnicalIndicator

logger = logging.getLogger(__name__)

def run_database_housekeeping_job():
    """
    오래된 데이터를 삭제하여 데이터베이스 크기를 관리하는 유지보수 작업을 실행합니다.
    (intraday_ohlcv, technical_indicators 테이블 대상)
    """
    logger.info("JOB START: Database housekeeping job...")
    db = next(get_db())
    try:
        # 설정 파일에 정의된 보관 기간을 기준으로 삭제 날짜를 계산합니다.
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)
        logger.info(f"Deleting data older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} UTC...")

        # 1. intraday_ohlcv 테이블에서 오래된 데이터 삭제
        ohlcv_deleted_count = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.timestamp_utc < cutoff_date
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {ohlcv_deleted_count} rows from 'intraday_ohlcv'.")

        # 2. technical_indicators 테이블에서 오래된 데이터 삭제
        indicators_deleted_count = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.timestamp_utc < cutoff_date
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {indicators_deleted_count} rows from 'technical_indicators'.")

        db.commit()
        logger.info("JOB END: Database housekeeping job completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred during database housekeeping: {e}")
        db.rollback()
    finally:
        db.close() 