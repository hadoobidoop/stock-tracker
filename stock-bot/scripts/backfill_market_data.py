"""
과거 시장 지표 데이터 백필(Backfill) 유틸리티

지정된 기간 동안의 모든 또는 특정 거시 경제 지표 데이터를 수집하여 데이터베이스에 저장합니다.

사용 예시:
# 모든 지표 백필
python scripts/backfill_market_data.py --start-date 2023-01-01 --end-date 2023-12-31

# 특정 지표(VIX, FEAR_GREED_INDEX)만 백필
python scripts/backfill_market_data.py --start-date 2023-01-01 --end-date 2023-12-31 --indicators VIX FEAR_GREED_INDEX
"""
import argparse
from datetime import datetime, date
import sys
import os
from typing import List, Optional

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from domain.stock.service.market_data_service import MarketDataService
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import setup_logging, get_logger

logger = get_logger(__name__)

def backfill_data(start_date: date, end_date: date, indicators: Optional[List[str]] = None):
    """지정된 기간 동안의 시장 데이터를 백필합니다."""
    logger.info(f"Starting market data backfill from {start_date} to {end_date} for indicators: {indicators or 'ALL'}")
    
    service = MarketDataService()
    
    # MarketDataService의 백필 메소드 호출
    success = service.backfill_all_indicators(start_date, end_date, indicators=indicators)
    
    if success:
        logger.info("Market data backfill process completed successfully.")
    else:
        logger.error("Market data backfill process failed for one or more indicators.")

def main():
    """스크립트 메인 실행 함수"""
    setup_logging()
    
    # 선택 가능한 지표 목록 생성
    available_indicators = [e.value for e in MarketIndicatorType]
    
    parser = argparse.ArgumentParser(
        description="Backfill market indicator data for a specified period.",
        formatter_class=argparse.RawTextHelpFormatter # 도움말 포맷 유지
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(),
        help="The start date for backfilling data (format: YYYY-MM-DD)."
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(),
        help="The end date for backfilling data (format: YYYY-MM-DD)."
    )
    parser.add_argument(
        '--indicators',
        nargs='+',  # 하나 이상의 인자를 리스트로 받음
        choices=available_indicators,
        metavar='INDICATOR',
        help=(
            "Optional: List of specific indicators to backfill.\n"
            "If not provided, all indicators will be backfilled.\n"
            f"Available choices: {', '.join(available_indicators)}"
        )
    )
    
    args = parser.parse_args()
    
    if args.start_date > args.end_date:
        logger.error("Start date cannot be after end date.")
        return
        
    backfill_data(args.start_date, args.end_date, args.indicators)

if __name__ == "__main__":
    main()