from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from infrastructure.logging import get_logger
from infrastructure.scheduler.jobs import realtime_signal_detection_job, update_stock_metadata_job, daily_ohlcv_update_job, hourly_ohlcv_update_job
from infrastructure.scheduler import settings

logger = get_logger(__name__)


def setup_scheduler():
    """스케줄러를 초기화하고 모든 작업을 등록합니다."""

    scheduler = BackgroundScheduler(timezone=pytz.timezone(settings.TIMEZONE))

    # 작업 1: 매주 월요일 새벽 메타데이터 업데이트
    scheduler.add_job(
        update_stock_metadata_job,
        trigger=CronTrigger(**settings.METADATA_UPDATE_JOB['cron']),
        id=settings.METADATA_UPDATE_JOB['id'],
        name=settings.METADATA_UPDATE_JOB['name']
    )

    # 작업 2: 장 중 실시간 신호 감지
    scheduler.add_job(
        realtime_signal_detection_job,
        trigger=CronTrigger(**settings.REALTIME_SIGNAL_JOB['cron']),
        id=settings.REALTIME_SIGNAL_JOB['id'],
        name=settings.REALTIME_SIGNAL_JOB['name']
    )

    # 작업 3: 일봉 OHLCV 데이터 업데이트
    scheduler.add_job(
        daily_ohlcv_update_job,
        trigger=CronTrigger(**settings.DAILY_OHLCV_UPDATE_JOB['cron']),
        id=settings.DAILY_OHLCV_UPDATE_JOB['id'],
        name=settings.DAILY_OHLCV_UPDATE_JOB['name']
    )

    # 작업 4: 1시간봉 OHLCV 데이터 업데이트
    scheduler.add_job(
        hourly_ohlcv_update_job,
        trigger=CronTrigger(**settings.HOURLY_OHLCV_UPDATE_JOB['cron']),
        id=settings.HOURLY_OHLCV_UPDATE_JOB['id'],
        name=settings.HOURLY_OHLCV_UPDATE_JOB['name']
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
