"""
실시간 신호 감지 스케줄러 작업
Infrastructure layer에서 Domain layer의 서비스를 호출하는 얇은 래퍼
"""
from infrastructure.logging import get_logger
from domain.signals.service.realtime.realtime_signal_detection_service import (
    RealtimeSignalDetectionJob,
    realtime_signal_detection_job
)

logger = get_logger(__name__)


def scheduled_realtime_signal_detection():
    """스케줄러에서 호출되는 실시간 신호 감지 작업"""
    try:
        logger.info("Starting scheduled realtime signal detection...")
        realtime_signal_detection_job()
        logger.info("Scheduled realtime signal detection completed.")
    except Exception as e:
        logger.error(f"Scheduled realtime signal detection failed: {e}")
        raise


# Backward compatibility
realtime_signal_detection_job_function = scheduled_realtime_signal_detection

if __name__ == "__main__":
    from infrastructure.logging import setup_logging
    setup_logging()
    scheduled_realtime_signal_detection()