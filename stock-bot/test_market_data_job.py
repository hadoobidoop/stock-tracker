"""
시장 데이터 수집 배치 잡 테스트 스크립트
"""
from infrastructure.logging import setup_logging
from infrastructure.scheduler.jobs.market_data_update_job import market_data_update_job

if __name__ == '__main__':
    # 로깅 설정
    setup_logging()
    
    print("=== Market Data Update Job Test ===")
    print("Testing Buffett Indicator, VIX, and Treasury Yield collection...")
    
    # 배치 잡 실행
    market_data_update_job()
    
    print("=== Test Completed ===")
    print("Check the logs above for detailed results.")