#!/usr/bin/env python3
"""
실시간 신호 감지 작업 테스트 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.logging import setup_logging, get_logger
from infrastructure.db.db_manager import create_db_and_tables
from infrastructure.scheduler.jobs.realtime_signal_detection_job import realtime_signal_detection_job

def main():
    """메인 테스트 함수"""
    # 로깅 설정
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("========================================")
    logger.info("  Testing Real-time Signal Detection Job")
    logger.info("========================================")
    
    try:
        # 1. 데이터베이스 초기화
        logger.info("Step 1: Initializing database...")
        create_db_and_tables()
        
        # 2. 실시간 신호 감지 작업 실행
        logger.info("Step 2: Running real-time signal detection job...")
        realtime_signal_detection_job()
        
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 