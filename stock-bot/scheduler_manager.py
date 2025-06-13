# scheduler_manager.py

import logging
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 설정과 작업 함수들 import
from config import DAILY_PREDICTION_HOUR_ET, DAILY_PREDICTION_MINUTE_ET, COLLECTION_INTERVAL_MINUTES
from jobs import update_stock_metadata_from_yfinance, run_daily_buy_price_prediction_job, \
    run_realtime_signal_detection_job, run_database_housekeeping_job, \
    run_intraday_data_correction_job, run_daily_ohlcv_correction_job, \
    run_intraday_data_collection_job

logger = logging.getLogger(__name__)


def setup_scheduler():
    """스케줄러를 초기화하고 모든 작업을 등록합니다."""

    scheduler = BackgroundScheduler(timezone=pytz.timezone('America/New_York'))

    # 작업 1: 매주 월요일 새벽 메타데이터 업데이트
    scheduler.add_job(
        update_stock_metadata_from_yfinance,
        trigger=CronTrigger(day_of_week='mon', hour=2, minute=30),
        id='weekly_metadata_update_job',
        name='Weekly Stock Metadata Update'
    )

    # 작업 2: 매일 장 마감 후 다음 날 가격 예측
    scheduler.add_job(
        run_daily_buy_price_prediction_job,
        trigger=CronTrigger(day_of_week='mon-fri', hour=DAILY_PREDICTION_HOUR_ET, minute=DAILY_PREDICTION_MINUTE_ET),
        id='daily_prediction_job',
        name='Daily Buy Price Prediction'
    )

    # 작업 3: 장 중 실시간 신호 감지
    scheduler.add_job(
        run_realtime_signal_detection_job,
        trigger=CronTrigger(day_of_week='mon-fri', hour='9-16', minute=1), # 월-금, 장중 시간(9시-16시), 매시 1분에 실행
        id='realtime_signal_job',
        name='Real-time Signal Detection (Hourly)'
    )

    # 작업 4: 데이터베이스 유지보수 (매주 일요일 새벽 4시 5분)
    scheduler.add_job(
        run_database_housekeeping_job,
        trigger=CronTrigger(day_of_week='sun', hour=4, minute=5),
        id='database_housekeeping_job',
        name='Database Housekeeping (Delete old data)'
    )

    # 작업 5: 장 마감 후 1분봉 데이터 보정 (매일 16:30)
    scheduler.add_job(
        run_intraday_data_correction_job,
        trigger=CronTrigger(day_of_week='mon-fri', hour=16, minute=30),
        id='intraday_data_correction_job',
        name='Intraday OHLCV Data Correction'
    )

    # 작업 6: 일봉 데이터 보정 (매일 17:00)
    scheduler.add_job(
        run_daily_ohlcv_correction_job,
        trigger=CronTrigger(day_of_week='mon-fri', hour=17, minute=0),
        id='daily_ohlcv_correction_job',
        name='Daily OHLCV Data Correction'
    )

    # 작업 7: 장중 1분봉 데이터 수집 (매일 9:30-16:00, 5분 간격)
    scheduler.add_job(
        run_intraday_data_collection_job,
        trigger=CronTrigger(day_of_week='mon-fri', hour='9-16', minute='*/5'),  # 매 5분마다 실행
        id='intraday_data_collection_job',
        name='Intraday OHLCV Data Collection'
    )

    return scheduler


def print_scheduled_jobs(scheduler):
    """예약된 모든 작업의 목록과 다음 실행 시간을 출력합니다."""
    logger.info("--- Scheduled Jobs Summary ---")
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else 'N/A'
        logger.info(f"-> Job: '{job.name}' | Trigger: {str(job.trigger)} | Next Run: {next_run}")
    logger.info("----------------------------")


def start_scheduler(scheduler):
    """스케줄러를 시작하고 상태를 출력합니다."""
    try:
        scheduler.start()
        print_scheduled_jobs(scheduler)
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        while True:
            import time
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully.")
