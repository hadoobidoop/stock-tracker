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

        from domain.analysis.strategy.strategy_factory import StrategyFactory
        is_supported, strategy_class = StrategyFactory.is_strategy_supported(strategy_name)

        if not is_supported:
            raise ValueError(f"Strategy '{strategy_name}' is not supported or not found.")

        if strategy_class == "static":
            strategy_type = StrategyType(strategy_name.lower())
            return self._run_specific_strategy_backtest(strategy_type=strategy_type, **kwargs)
        
        elif strategy_class == "dynamic":
            return self._run_dynamic_strategy_backtest(dynamic_strategy_name=strategy_name, **kwargs)
        
        else:
            raise NotImplementedError(f"Backtesting for strategy class '{strategy_class}' is not implemented.")

    def run_comparison(self, strategies: List[str], **kwargs) -> Dict[str, Any]:
        """여러 전략의 성과를 비교 분석합니다."""
        logger.info(f"Comparing performance for strategies: {', '.join(strategies)}")
        
        all_results = {}
        from domain.analysis.strategy.strategy_factory import StrategyFactory

        for name in strategies:
            is_supported, strategy_class = StrategyFactory.is_strategy_supported(name)
            if not is_supported:
                logger.warning(f"Strategy '{name}' is not supported and will be skipped in comparison.")
                continue

            try:
                if strategy_class == "static":
                    result = self._run_specific_strategy_backtest(strategy_type=StrategyType(name.lower()), **kwargs)
                    all_results[name] = result
                elif strategy_class == "dynamic":
                    result = self._run_dynamic_strategy_backtest(dynamic_strategy_name=name, **kwargs)
                    all_results[name] = result
            except Exception as e:
                logger.error(f"Error running backtest for '{name}' in comparison mode: {e}", exc_info=True)

        return self._create_comparison_report(all_results)
    
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

    def _create_comparison_report(self, all_results: Dict[str, BacktestResult]) -> Dict[str, Any]:
        """여��� 백테스트 결과로부터 비교 리포트를 생성합니다."""
        strategy_analysis = {}
        best_strategy, best_sharpe = None, float('-inf')

        for strategy_name, result in all_results.items():
            analysis = {
                'total_return_percent': result.total_return_percent,
                'annualized_return_percent': result.annualized_return_percent,
                'max_drawdown_percent': result.max_drawdown_percent,
                'sharpe_ratio': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'profit_factor': result.profit_factor,
                'final_capital': result.final_capital
            }
            strategy_analysis[strategy_name] = analysis
            if result.sharpe_ratio > best_sharpe:
                best_sharpe, best_strategy = result.sharpe_ratio, strategy_name
        
        start_date = next(iter(all_results.values())).start_date if all_results else None
        end_date = next(iter(all_results.values())).end_date if all_results else None

        comparison_summary = {
            'best_strategy': best_strategy,
            'strategies_tested': len(all_results),
            'comparison_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}" if start_date and end_date else "N/A",
            'ranking_by_sharpe': sorted([(n, d['sharpe_ratio']) for n, d in strategy_analysis.items()], key=lambda x: x[1], reverse=True),
            'ranking_by_return': sorted([(n, d['total_return_percent']) for n, d in strategy_analysis.items()], key=lambda x: x[1], reverse=True)
        }
        logger.info(f"Strategy comparison completed. Best strategy: {best_strategy} (Sharpe: {best_sharpe:.2f})")
        return {'strategy_results': all_results, 'strategy_analysis': strategy_analysis, 'comparison_summary': comparison_summary}
    
    def run_parameter_optimization(self,
    
    # ... (이하 다른 private 헬퍼 메서드들은 그대로 유지) ...
 