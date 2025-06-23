"""
APScheduler 작업의 모든 설정을 중앙에서 관리합니다.
Cron 표현식, 작업 ID, 이름 등을 이곳에서 정의합니다.
"""

# --- 타임존 설정 ---
TIMEZONE = 'America/New_York'

# --- 작업별 설정 ---

# 1. 주간 주식 메타데이터 업데이트 작업 설정
METADATA_UPDATE_JOB = {
    'id': 'weekly_metadata_update_job',
    'name': 'Weekly Stock Metadata Update',
    'cron': {
        'day_of_week': 'mon',
        'hour': 2,
        'minute': 30
    }
}

# 2. 장중 실시간 신호 감지 작업 설정
REALTIME_SIGNAL_JOB = {
    'id': 'realtime_signal_job',
    'name': 'Real-time Signal Detection (Hourly)',
    'cron': {
        'day_of_week': 'mon-fri',
        'hour': '9-16',
        'minute': '*/30'
    }
}

# 3. 일봉 OHLCV 데이터 업데이트 작업 설정
DAILY_OHLCV_UPDATE_JOB = {
    'id': 'daily_ohlcv_update_job',
    'name': 'Daily OHLCV Data Update',
    'cron': {
        'day_of_week': 'mon-fri',  # 월-금 (장날만)
        'hour': 17,                # 오후 5시 (장 마감 후)
        'minute': 0
    }
}

# 4. 1시간봉 OHLCV 데이터 업데이트 작업 설정
HOURLY_OHLCV_UPDATE_JOB = {
    'id': 'hourly_ohlcv_update_job',
    'name': 'Hourly OHLCV Data Update',
    'cron': {
        'day_of_week': 'mon-fri',  # 월-금 (장날만)
        'hour': '9-16',            # 9시-16시 (장 시간)
        'minute': 10               # 매시 10분
    }
}

# 5. 시장 데이터 업데이트 작업 설정 (버핏 지수, VIX 등)
MARKET_DATA_UPDATE_JOB = {
    'id': 'market_data_update_job',
    'name': 'Market Indicators Update (Buffett, VIX, etc.)',
    'cron': {
        'day_of_week': 'mon-fri',  # 월-금 (장날만)
        'hour': 18,                # 오후 6시 (일봉 업데이트 후)
        'minute': 0
    }
}
