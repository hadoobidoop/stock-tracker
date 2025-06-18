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
        'minute': '*' # 매분 실행으로 변경. 필요시 '*/5' 등으로 조절 가능
    }
}
