# --- 공통 로거 설정 ---
from infrastructure.logging import setup_logging, get_logger
from infrastructure.db.db_manager import create_db_and_tables
from infrastructure.scheduler.jobs import update_stock_metadata_job
from infrastructure.scheduler.scheduler_manager import setup_scheduler, start_scheduler

# 애플리케이션 시작 시 로깅 설정
setup_logging()
logger = get_logger(__name__)


if __name__ == "__main__":
    logger.info("========================================")
    logger.info("  Starting Stock Analyzer Bot")
    logger.info("========================================")

    # 1. 데이터베이스 테이블 확인 및 생성
    logger.info("Step 1: Initializing database...")
    create_db_and_tables()

    # 2. 프로그램 시작 시 메타데이터 즉시 업데이트
    logger.info("Step 2: Performing initial metadata update...")
    update_stock_metadata_job() # 이 함수를 찾을 수 없어 주석 처리합니다.

    # 3. 스케줄러 설정 및 시작
    logger.info("Step 3: Setting up and starting the scheduler...")
    scheduler = setup_scheduler()
    start_scheduler(scheduler)
