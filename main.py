# main.py (Refactored)

import logging

# 필요한 모듈만 import
from database_setup import create_db_and_tables
from jobs import update_stock_metadata_from_yfinance
from scheduler_manager import setup_scheduler, start_scheduler

# --- 로깅 설정 (프로젝트의 다른 파일에서도 사용 가능) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
        # logging.FileHandler("stock_analyzer.log") # 파일 로깅이 필요하면 활성화
    ]
)

if __name__ == "__main__":
    logging.info("========================================")
    logging.info("  Starting Stock Analyzer Bot")
    logging.info("========================================")

    # 1. 데이터베이스 테이블 확인 및 생성
    logging.info("Step 1: Initializing database...")
    create_db_and_tables()

    # 2. 프로그램 시작 시 메타데이터 즉시 업데이트
    logging.info("Step 2: Performing initial metadata update...")
    update_stock_metadata_from_yfinance()

    # 3. 스케줄러 설정 및 시작
    logging.info("Step 3: Setting up and starting the scheduler...")
    scheduler = setup_scheduler()
    start_scheduler(scheduler)
