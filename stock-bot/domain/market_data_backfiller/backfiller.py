# domain/market_data_backfiller/backfiller.py
from datetime import datetime
import time
from typing import List, Dict, Any, Optional

from .config import ENABLED_PROVIDERS as DEFAULT_ENABLED_PROVIDERS, BACKFILL_PROVIDERS_CONFIG
from .providers import *
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataBackfiller:
    """
    설정 파일을 기반으로 다양한 시장 데이터 Provider를 실행하여,
    지정된 기간 동안의 과거 데이터를 채우는 오케스트레이터입니다.
    """

    def __init__(self, enabled_providers: Optional[List[str]] = None, inter_provider_delay: float = 1.0):
        """
        :param enabled_providers: 백필을 실행할 Provider의 이름 리스트. None이면 config.py의 기본 설정을 사용합니다.
        :param inter_provider_delay: 각 Provider 실행 후 API 호출 제한을 피하기 위한 대기 시간 (초)
        """
        self.providers: List[BaseBackfillProvider] = []
        self.inter_provider_delay = inter_provider_delay
        
        # 사용할 Provider 목록 결정
        providers_to_enable = enabled_providers if enabled_providers is not None else DEFAULT_ENABLED_PROVIDERS
        self._initialize_providers(providers_to_enable)

    def _initialize_providers(self, enabled_providers: List[str]):
        """
        주어진 목록을 기반으로 Provider 인스턴스를 생성합니다.
        """
        provider_classes = {
            "FredBackfillProvider": FredBackfillProvider,
            "YahooBackfillProvider": YahooBackfillProvider,
            "FearGreedBackfillProvider": FearGreedBackfillProvider,
            "PutCallRatioBackfillProvider": PutCallRatioBackfillProvider,
        }

        logger.info(f"Initializing providers for: {enabled_providers}")
        for provider_name in enabled_providers:
            if provider_name in BACKFILL_PROVIDERS_CONFIG:
                config = BACKFILL_PROVIDERS_CONFIG[provider_name]
                provider_class_name = config.get("provider")
                provider_class = provider_classes.get(provider_class_name)

                if provider_class:
                    args = {k: v for k, v in config.items() if k != "provider"}
                    try:
                        self.providers.append(provider_class(**args))
                        logger.info(f"Initialized provider: {provider_class_name} for {provider_name}")
                    except Exception as e:
                        logger.error(f"Failed to initialize provider {provider_class_name} for {provider_name}: {e}")
                else:
                    logger.error(f"Provider class not found: {provider_class_name}")
            else:
                logger.error(f"Configuration not found for enabled provider: {provider_name}")

    def run(self, start_date_str: str, end_date_str: str):
        """
        활성화된 모든 Provider를 실행하여 데이터 백필을 수행합니다.
        """
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            return

        logger.info(f"--- Starting Market Data Backfill for {start_date} to {end_date} ---")
        
        results: Dict[str, bool] = {}
        for i, provider in enumerate(self.providers):
            provider_id = f"{provider.provider_name}({getattr(provider, 'symbol', '') or getattr(provider, 'indicator_type').value})"
            try:
                success = provider.backfill(start_date, end_date)
                results[provider_id] = success
            except Exception as e:
                logger.error(f"An unexpected error occurred in provider {provider_id}: {e}", exc_info=True)
                results[provider_id] = False
            
            if i < len(self.providers) - 1:
                logger.info(f"Waiting for {self.inter_provider_delay} seconds before next provider...")
                time.sleep(self.inter_provider_delay)
        
        logger.info("--- Backfill Process Summary ---")
        for provider_id, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"- {provider_id}: {status}")
        logger.info("---------------------------------")


def main(start_date: str, end_date: str, indicators: Optional[List[str]] = None):
    """
    시장 데이터 백필러를 실행하는 메인 함수입니다.

    :param start_date: 백필 시작 날짜 (YYYY-MM-DD 형식)
    :param end_date: 백필 종료 날짜 (YYYY-MM-DD 형식)
    :param indicators: 백필할 지표 이름 리스트. None이면 config.py의 기본 설정을 사용합니다.
    """
    backfiller = MarketDataBackfiller(enabled_providers=indicators)
    backfiller.run(start_date, end_date)

if __name__ == '__main__':
    from infrastructure.logging import setup_logging
    setup_logging()
    
    # 예시 1: config.py에 정의된 모든 활성화된 지표를 백필
    # main(start_date="2024-01-01", end_date="2024-07-01")
    
    # 예시 2: VIX와 DXY만 특정하여 백필
    main(start_date="2024-06-01", end_date="2024-07-01", indicators=["FEAR_GREED_INDEX"])