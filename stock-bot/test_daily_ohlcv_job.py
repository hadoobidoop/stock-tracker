#!/usr/bin/env python3
"""
일봉 OHLCV 데이터 업데이트 작업 테스트 스크립트

이 스크립트는 daily_ohlcv_update_job을 수동으로 실행하여 
Yahoo Finance에서 6개월치 일봉 데이터를 가져와 데이터베이스에 저장합니다.

사용법:
    python test_daily_ohlcv_job.py
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infrastructure.logging import setup_logging, get_logger
from infrastructure.scheduler.jobs.daily_ohlcv_update_job import daily_ohlcv_update_job
from infrastructure.db import init_db

def main():
    """테스트 메인 함수"""
    # 로깅 설정
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info("일봉 OHLCV 데이터 업데이트 작업 테스트 시작")
    logger.info("="*60)
    
    try:
        # 데이터베이스 초기화 (테이블 생성)
        logger.info("데이터베이스 초기화 중...")
        init_db()
        logger.info("데이터베이스 초기화 완료")
        
        # 일봉 데이터 업데이트 작업 실행
        daily_ohlcv_update_job()
        
        logger.info("="*60)
        logger.info("일봉 OHLCV 데이터 업데이트 작업 테스트 완료")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 