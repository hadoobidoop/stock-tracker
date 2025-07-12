# domain/market_data_backfiller/backfiller.py
import argparse
from datetime import datetime
import time
from typing import List, Dict, Any, Optional

from domain.market_data_backfiller.providers.buffett_provider import BuffettBackfillProvider
from .config import ENABLED_PROVIDERS as DEFAULT_ENABLED_PROVIDERS, BACKFILL_PROVIDERS_CONFIG
from .providers import *
from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataBackfiller:
    """
    설정 파일을 기반으로 다양한 시장 데이터 Provider를 실행하여,
    지정된 기간 동안의 과거 데이터를 채우는 오케스트레이터입니다.
    """

    def __init__(self, enabled_indicators: Optional[List[str]] = None, inter_provider_delay: float = 1.0):
        self.repository = SQLMarketDataRepository()
        self.providers: List[BaseBackfillProvider] = []
        self.inter_provider_delay = inter_provider_delay
        
        indicators_to_run = enabled_indicators if enabled_indicators is not None else DEFAULT_ENABLED_PROVIDERS
        self._initialize_providers(indicators_to_run)

    def _initialize_providers(self, indicators_to_run: List[str]):
        """주어진 지표 목록을 기반으로 필요한 Provider 인스턴스를 중복 없이 생성합니다."""
        provider_classes = {
            "FredBackfillProvider": FredBackfillProvider,
            "YahooBackfillProvider": YahooBackfillProvider,
            "FearGreedBackfillProvider": FearGreedBackfillProvider,
            "PutCallRatioBackfillProvider": PutCallRatioBackfillProvider,
            "BuffettBackfillProvider": BuffettBackfillProvider,
        }
        
        initialized_groups = set()
        for indicator_name in indicators_to_run:
            if indicator_name not in BACKFILL_PROVIDERS_CONFIG:
                logger.warning(f"Configuration not found for indicator: {indicator_name}. Skipping.")
                continue

            config = BACKFILL_PROVIDERS_CONFIG[indicator_name]
            provider_class_name = config.get("provider")
            group = config.get("group")

            # 그룹화된 Provider는 한 번만 초기화
            if group and group in initialized_groups:
                continue
            
            provider_class = provider_classes.get(provider_class_name)
            if not provider_class:
                logger.error(f"Provider class not found: {provider_class_name}")
                continue
            
            try:
                args = {}
                if provider_class_name in ["FredBackfillProvider", "YahooBackfillProvider"]:
                    args = {"symbol": config["symbol"], "indicator_type": config["indicator_type"]}
                
                self.providers.append(provider_class(**args))
                logger.info(f"Initialized provider: {provider_class_name} for {group or indicator_name}")

                if group:
                    initialized_groups.add(group)
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_class_name}: {e}", exc_info=True)

    def run(self, start_date: datetime.date, end_date: datetime.date):
        """활성화된 모든 Provider를 실행하고, 반환된 데이터를 DB에 저장합니다."""
        logger.info(f"--- Starting Market Data Backfill for {start_date} to {end_date} ---")
        
        all_records_to_save = []
        for provider in self.providers:
            try:
                records = provider.backfill(start_date, end_date)
                if records:
                    all_records_to_save.extend(records)
                
                # API 호출 제한 방지
                if len(self.providers) > 1:
                    logger.info(f"Waiting for {self.inter_provider_delay} seconds...")
                    time.sleep(self.inter_provider_delay)
            except Exception as e:
                logger.error(f"Provider {provider.provider_name} failed during execution: {e}", exc_info=True)

        if not all_records_to_save:
            logger.info("No new data to save from any provider.")
            return

        # 모든 데이터를 한 번에 필터링하고 저장
        try:
            logger.info(f"Total records parsed from all providers: {len(all_records_to_save)}")
            
            # DB에 이미 있는 데이터 필터링
            final_records = []
            all_types = {record['indicator_type'] for record in all_records_to_save}
            existing_dates_map = {itype: self.repository.get_existing_dates(itype, start_date) for itype in all_types}

            for record in all_records_to_save:
                if record['date'] not in existing_dates_map.get(record['indicator_type'], set()):
                    final_records.append(record)
            
            if not final_records:
                logger.info("All parsed data already exists in the database.")
                return

            # --- 디버깅 로그 추가 ---
            logger.debug(f"Final records to be saved (first 5): {final_records[:5]}")

            # 단일 트랜잭션으로 배치 저장
            with self.repository.transaction() as session:
                self.repository.save_market_data_batch(final_records, session)
            
            logger.info(f"--- Backfill Process Finished: Successfully saved {len(final_records)} new records. ---")

        except Exception as e:
            logger.error(f"Failed to save batch data to the database: {e}", exc_info=True)


def main(args):
    """명령줄 인자를 받아 시장 데이터 백필러를 실행하는 메인 함수입니다."""
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    backfiller = MarketDataBackfiller(enabled_indicators=args.indicators)
    backfiller.run(start_date, end_date)

if __name__ == '__main__':
    from infrastructure.logging import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Market Data Backfiller CLI")
    parser.add_argument('--start_date', type=str, required=True, help='백필 시작 날짜 (YYYY-MM-DD 형식)')
    parser.add_argument('--end_date', type=str, required=True, help='백필 종료 날짜 (YYYY-MM-DD 형식)')
    parser.add_argument('--indicators', type=str, nargs='*', default=None, help='백필할 지표 이름 리스트. 없으면 config.py의 기본값을 사용합니다.')
    
    args = parser.parse_args()
    main(args)

