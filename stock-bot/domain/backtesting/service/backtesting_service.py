from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import json

from infrastructure.logging import get_logger
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from domain.analysis.repository.analysis_repository import MarketDataRepository
from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository

# 새로운 전략 시스템 import
from domain.analysis.config.static_strategies import StrategyType, STRATEGY_CONFIGS
from domain.analysis.strategy.strategy_manager import StrategyManager

from ..engine.backtesting_engine import BacktestingEngine
from ..models.backtest_result import BacktestResult

logger = get_logger(__name__)


class BacktestingService:
    """백테스팅 서비스 - 단순화된 인터페이스 제공"""
    
    def __init__(self, 
                 stock_repository: Optional[StockRepository] = None,
                 market_data_repository: Optional[MarketDataRepository] = None):
        self.stock_repository = stock_repository or SQLStockRepository()
        self.market_data_repository = market_data_repository or SQLMarketDataRepository()
        self.stock_analysis_service = StockAnalysisService(self.stock_repository)
        logger.info("BacktestingService initialized.")

    def run_single_analysis(self, strategy_name: str, **kwargs) -> BacktestResult:
        """단일 전략을 심층 분석합니다."""
        logger.info(f"Running deep-dive analysis for single strategy: {strategy_name}")
        
        # TODO: strategy_name을 기반으로 정적/동적 전략을 식별하고,
        #       해당하는 내부 백테스트 메서드를 호출하는 로직 구현 필요.
        
        # 임시 구현: 정적 전략만 지원
        try:
            strategy_type = StrategyType[strategy_name]
            return self._run_specific_strategy_backtest(strategy_type=strategy_type, **kwargs)
        except KeyError:
            # 동적 전략 등 다른 타입 처리 필요
            raise NotImplementedError(f"Strategy type for '{strategy_name}' is not yet supported in single analysis mode.")

    def run_comparison(self, strategies: List[str], **kwargs) -> Dict[str, Any]:
        """여러 전략의 성과를 비교 분석합니다."""
        logger.info(f"Comparing performance for strategies: {', '.join(strategies)}")
        
        # TODO: strategies 리스트에 포함된 정적/동적 전략들을 모두 실행하고,
        #       결과를 취합하여 비교 리포트를 생성하는 로직 구현 필요.
        
        # 임시 구현: 정적 전략만 지원
        static_strategies = []
        for name in strategies:
            try:
                static_strategies.append(StrategyType[name])
            except KeyError:
                logger.warning(f"Strategy '{name}' is not a valid static strategy and will be skipped.")
        
        return self._compare_all_strategies(strategies=static_strategies, **kwargs)
    
    # ... (이하 모든 _run... 및 compare_all_strategies 메서드는 private으로 변경) ...
    
    def _run_specific_strategy_backtest(self,
                                     tickers: List[str],
                                     start_date: datetime,
                                     end_date: datetime,
                                     strategy_type: StrategyType,
                                     initial_capital: float,
                                     commission_rate: float,
                                     risk_per_trade: float,
                                     data_interval: str) -> BacktestResult:
        # ... (기존 코드와 동일)
        pass

    def _run_strategy_mix_backtest(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                mix_name: str,
                                initial_capital: float,
                                commission_rate: float,
                                risk_per_trade: float,
                                data_interval: str) -> BacktestResult:
        # ... (기존 코드와 동일)
        pass

    def _run_dynamic_strategy_backtest(self,
                                    tickers: List[str],
                                    start_date: datetime,
                                    end_date: datetime,
                                    dynamic_strategy_name: str,
                                    initial_capital: float,
                                    commission_rate: float,
                                    risk_per_trade: float,
                                    data_interval: str) -> BacktestResult:
        # ... (기존 코드와 동일)
        pass

    def _run_auto_strategy_backtest(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 initial_capital: float,
                                 commission_rate: float,
                                 risk_per_trade: float,
                                 data_interval: str) -> BacktestResult:
        # ... (기존 코드와 동일)
        pass

    def _compare_all_strategies(self,
                             tickers: List[str],
                             start_date: datetime,
                             end_date: datetime,
                             initial_capital: float = 100000.0,
                             commission_rate: float = 0.001,
                             risk_per_trade: float = 0.02,
                             data_interval: str = '1h',
                             strategies: List[StrategyType] = None) -> Dict[str, Any]:
        # ... (기존 코드와 동일)
        pass
    
    # ... (이하 다른 private 헬퍼 메서드들은 그대로 유지) ...
 