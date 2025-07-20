"""Scheduler Jobs Package."""
from .daily_ohlcv_update_job import daily_ohlcv_update_job
from .hourly_ohlcv_update_job import hourly_ohlcv_update_job
from .market_data_update_job import market_data_update_job
# from .realtime_signal_detection_job import scheduled_realtime_signal_detection as realtime_signal_detection_job  # 임시 비활성화
from .update_stock_metadata_job import update_stock_metadata_job

# 임시 더미 함수
def realtime_signal_detection_job():
    """임시 더미 함수 - Phase 4에서 새로운 services 계층으로 대체 예정"""
    print("realtime_signal_detection_job 임시 비활성화 (Phase 4 진행 중)")

__all__ = [
    'update_stock_metadata_job',
    'realtime_signal_detection_job',
    'daily_ohlcv_update_job',
    'hourly_ohlcv_update_job',
    'market_data_update_job',
]
