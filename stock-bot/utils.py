# utils.py

import pytz
from datetime import datetime

def get_current_et_time():
    """현재 ET(미국 동부 시간)를 반환합니다."""
    et_timezone = pytz.timezone('America/New_York')
    return datetime.now(et_timezone)

def is_market_open(current_et: datetime) -> bool:
    """
    미국 주식 시장이 현재 열려있는지 확인합니다 (주중 오전 9:30 ~ 오후 4:00 ET).
    """
    if current_et.weekday() >= 5: # 주말 (토요일=5, 일요일=6)
        return False

    market_open_time = current_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close_time = current_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open_time <= current_et < market_close_time
