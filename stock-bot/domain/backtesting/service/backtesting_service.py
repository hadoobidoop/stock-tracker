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
    """백테스팅 서비스 - 다중 전략 시스템 지원"""
    
    def __init__(self, 
                 stock_repository: Optional[StockRepository] = None,
                 market_data_repository: Optional[MarketDataRepository] = None):
        self.stock_repository = stock_repository or SQLStockRepository()
        self.market_data_repository = market_data_repository or SQLMarketDataRepository()
        self.stock_analysis_service = StockAnalysisService(self.stock_repository)
        logger.info("BacktestingService initialized with multi-strategy support")

    def run_backtest(self, mode: str, **kwargs) -> Any:
        """
        백테스팅을 위한 단일 진입점.
        mode에 따라 적절한 내부 백테스팅 메서드를 호출합니다.
        """
        logger.info(f"Received backtest request with mode: {mode}")

        # 공통 파라미터 추출
        tickers = kwargs.get("tickers")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        initial_capital = kwargs.get("initial_capital", 100000.0)
        commission_rate = kwargs.get("commission_rate", 0.001)
        risk_per_trade = kwargs.get("risk_per_trade", 0.02)
        data_interval = kwargs.get("data_interval", '1h')

        if mode == 'strategy':
            return self._run_specific_strategy_backtest(
                strategy_type=kwargs.get("strategy_type"),
                tickers=tickers, start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, commission_rate=commission_rate,
                risk_per_trade=risk_per_trade, data_interval=data_interval
            )
        elif mode == 'strategy-mix':
            return self._run_strategy_mix_backtest(
                mix_name=kwargs.get("mix_name"),
                tickers=tickers, start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, commission_rate=commission_rate,
                risk_per_trade=risk_per_trade, data_interval=data_interval
            )
        elif mode == 'dynamic-strategy':
            return self._run_dynamic_strategy_backtest(
                dynamic_strategy_name=kwargs.get("dynamic_strategy_name"),
                tickers=tickers, start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, commission_rate=commission_rate,
                risk_per_trade=risk_per_trade, data_interval=data_interval
            )
        elif mode == 'auto-strategy':
            return self._run_auto_strategy_backtest(
                tickers=tickers, start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, commission_rate=commission_rate,
                risk_per_trade=risk_per_trade, data_interval=data_interval
            )
        elif mode == 'strategy-comparison':
            return self.compare_all_strategies(
                strategies=kwargs.get("strategies"),
                tickers=tickers, start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, commission_rate=commission_rate,
                risk_per_trade=risk_per_trade, data_interval=data_interval
            )
        # ... 다른 모드들도 여기에 추가 ...
        else:
            logger.error(f"Unsupported backtest mode: {mode}")
            raise ValueError(f"Unsupported backtest mode: {mode}")
    
    def _run_specific_strategy_backtest(self,
                                     tickers: List[str],
                                     start_date: datetime,
                                     end_date: datetime,
                                     strategy_type: StrategyType,
                                     initial_capital: float,
                                     commission_rate: float,
                                     risk_per_trade: float,
                                     data_interval: str) -> BacktestResult:
        """특정 전략으로 백테스트 실행"""
        logger.info(f"Running backtest with {strategy_type.value} strategy")
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital, commission_rate=commission_rate,
            risk_per_trade=risk_per_trade, use_enhanced_signals=True,
            strategy_type=strategy_type
        )
        result = engine.run_strategy_backtest(
            tickers=tickers, start_date=start_date, end_date=end_date,
            strategy_type=strategy_type, data_interval=data_interval
        )
        logger.info(f"{strategy_type.value} strategy backtest completed. Return: {result.total_return_percent:.2f}%")
        return result

    def _run_strategy_mix_backtest(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                mix_name: str,
                                initial_capital: float,
                                commission_rate: float,
                                risk_per_trade: float,
                                data_interval: str) -> BacktestResult:
        """전략 조합으로 백테스트 실행"""
        logger.info(f"Running backtest with strategy mix: {mix_name}")
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital, commission_rate=commission_rate,
            risk_per_trade=risk_per_trade, use_enhanced_signals=True,
            strategy_type=StrategyType.BALANCED
        )
        result = engine.run_strategy_mix_backtest(
            tickers=tickers, start_date=start_date, end_date=end_date,
            mix_name=mix_name, data_interval=data_interval
        )
        logger.info(f"Strategy mix '{mix_name}' backtest completed. Return: {result.total_return_percent:.2f}%")
        return result

    def _run_dynamic_strategy_backtest(self,
                                    tickers: List[str],
                                    start_date: datetime,
                                    end_date: datetime,
                                    dynamic_strategy_name: str,
                                    initial_capital: float,
                                    commission_rate: float,
                                    risk_per_trade: float,
                                    data_interval: str) -> BacktestResult:
        """동적 전략으로 백테스트 실행"""
        logger.info(f"Running backtest with dynamic strategy: {dynamic_strategy_name}")
        daily_market_data = self.market_data_repository.get_all_market_data_in_range(start_date, end_date)
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital, commission_rate=commission_rate,
            risk_per_trade=risk_per_trade, use_enhanced_signals=True,
            strategy_type=None
        )
        result = engine.run_dynamic_strategy_backtest(
            tickers=tickers, start_date=start_date, end_date=end_date,
            dynamic_strategy_name=dynamic_strategy_name, data_interval=data_interval,
            daily_market_data=daily_market_data
        )
        logger.info(f"Dynamic strategy '{dynamic_strategy_name}' backtest completed. Return: {result.total_return_percent:.2f}%")
        return result

    def _run_auto_strategy_backtest(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 initial_capital: float,
                                 commission_rate: float,
                                 risk_per_trade: float,
                                 data_interval: str) -> BacktestResult:
        """자동 전략 선택으로 백테스트 실행"""
        logger.info("Running backtest with automatic strategy selection")
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital, commission_rate=commission_rate,
            risk_per_trade=risk_per_trade, use_enhanced_signals=True,
            strategy_type=StrategyType.BALANCED
        )
        result = engine.run_auto_strategy_backtest(
            tickers=tickers, start_date=start_date, end_date=end_date,
            data_interval=data_interval
        )
        logger.info(f"Auto strategy selection backtest completed. Return: {result.total_return_percent:.2f}%")
        return result

    def compare_all_strategies(self,
                             tickers: List[str],
                             start_date: datetime,
                             end_date: datetime,
                             initial_capital: float = 100000.0,
                             commission_rate: float = 0.001,
                             risk_per_trade: float = 0.02,
                             data_interval: str = '1h',
                             strategies: List[StrategyType] = None) -> Dict[str, Any]:
        """모든 전략 또는 지정된 전략들을 비교"""
        if strategies is None:
            strategies = [
                StrategyType.CONSERVATIVE, StrategyType.BALANCED, StrategyType.AGGRESSIVE,
                StrategyType.MOMENTUM, StrategyType.TREND_FOLLOWING, StrategyType.CONTRARIAN
            ]
        logger.info(f"Comparing {len(strategies)} strategies")
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital, commission_rate=commission_rate,
            risk_per_trade=risk_per_trade, use_enhanced_signals=True,
            strategy_type=StrategyType.BALANCED
        )
        comparison_results = engine.compare_strategies(
            tickers=tickers, start_date=start_date, end_date=end_date,
            strategies=strategies, data_interval=data_interval
        )
        strategy_analysis = {}
        best_strategy, best_sharpe = None, float('-inf')
        for strategy_name, result in comparison_results.items():
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
        
        comparison_summary = {
            'best_strategy': best_strategy,
            'strategies_tested': len(strategies),
            'comparison_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'ranking_by_sharpe': sorted([(n, d['sharpe_ratio']) for n, d in strategy_analysis.items()], key=lambda x: x[1], reverse=True),
            'ranking_by_return': sorted([(n, d['total_return_percent']) for n, d in strategy_analysis.items()], key=lambda x: x[1], reverse=True)
        }
        logger.info(f"Strategy comparison completed. Best strategy: {best_strategy} (Sharpe: {best_sharpe:.2f})")
        return {'strategy_results': comparison_results, 'strategy_analysis': strategy_analysis, 'comparison_summary': comparison_summary}
    
    def run_parameter_optimization(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 parameter_ranges: Dict[str, List],
                                 initial_capital: float = 100000.0) -> Dict[str, Any]:
        """매개변수 최적화 백테스트"""
        logger.info("Starting parameter optimization backtest")
        optimization_results, best_result, best_return = [], None, float('-inf')
        param_combinations = self._generate_parameter_combinations(parameter_ranges)
        
        for i, params in enumerate(param_combinations):
            logger.info(f"Testing parameter set {i+1}/{len(param_combinations)}: {params}")
            try:
                result = self._run_specific_strategy_backtest(
                    tickers=tickers, start_date=start_date, end_date=end_date,
                    initial_capital=initial_capital, **params
                )
                result_summary = {
                    'parameters': params, 'total_return_percent': result.total_return_percent,
                    'sharpe_ratio': result.sharpe_ratio, 'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                }
                optimization_results.append(result_summary)
                if result.sharpe_ratio > best_return:
                    best_return, best_result = result.sharpe_ratio, result_summary
            except Exception as e:
                logger.error(f"Error in parameter optimization for {params}: {e}")
        
        return {
            'best_parameters': best_result, 'all_results': optimization_results,
            'optimization_summary': self._create_optimization_summary(optimization_results)
        }
    
    def run_walk_forward_analysis(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                train_period_months: int = 6,
                                test_period_months: int = 1,
                                initial_capital: float = 100000.0) -> Dict[str, Any]:
        """워크 포워드 분석"""
        logger.info("Starting walk forward analysis")
        walk_forward_results, current_date = [], start_date
        
        while current_date < end_date:
            train_end = current_date + timedelta(days=train_period_months * 30)
            test_start, test_end = train_end, min(train_end + timedelta(days=test_period_months * 30), end_date)
            logger.info(f"Training: {current_date} to {train_end}, Testing: {test_start} to {test_end}")
            try:
                test_result = self._run_specific_strategy_backtest(
                    tickers=tickers, start_date=test_start, end_date=test_end,
                    initial_capital=initial_capital, strategy_type=StrategyType.BALANCED
                )
                walk_forward_results.append({
                    'train_period': {'start': current_date, 'end': train_end},
                    'test_period': {'start': test_start, 'end': test_end},
                    'test_return_percent': test_result.total_return_percent,
                    'test_win_rate': test_result.win_rate
                })
            except Exception as e:
                logger.error(f"Error in walk forward period {current_date} to {test_end}: {e}")
            current_date = test_start
        
        return {'periods': walk_forward_results, 'summary': self._create_walk_forward_summary(walk_forward_results)}
    
    def compare_strategies(self,
                         tickers: List[str],
                         start_date: datetime,
                         end_date: datetime,
                         strategy_configs: Dict[str, Dict],
                         initial_capital: float = 100000.0) -> Dict[str, Any]:
        """다중 전략 비교 백테스트"""
        logger.info(f"Comparing {len(strategy_configs)} strategies")
        strategy_results = {}
        for name, config in strategy_configs.items():
            logger.info(f"Testing strategy: {name}")
            try:
                result = self._run_specific_strategy_backtest(
                    tickers=tickers, start_date=start_date, end_date=end_date,
                    initial_capital=initial_capital, strategy_type=StrategyType.BALANCED, **config
                )
                strategy_results[name] = {
                    'config': config, 'result': result,
                    'summary': {'total_return_percent': result.total_return_percent, 'sharpe_ratio': result.sharpe_ratio}
                }
            except Exception as e:
                logger.error(f"Error testing strategy {name}: {e}")
        
        return {'strategies': strategy_results, 'comparison': self._create_strategy_comparison(strategy_results)}
    
    def generate_report(self, result: BacktestResult, save_path: Optional[str] = None) -> Dict[str, Any]:
        """백테스트 결과 리포트 생성"""
        logger.info("Generating backtest report")
        report = {
            'executive_summary': {
                'backtest_period': f"{result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}",
                'total_return': f"{result.total_return_percent:.2f}%",
                'sharpe_ratio': f"{result.sharpe_ratio:.2f}"
            },
            'detailed_metrics': result.to_dict(),
            'monthly_performance': result.get_monthly_performance().to_dict('records') if not result.get_monthly_performance().empty else []
        }
        if save_path:
            try:
                with open(save_path, 'w') as f: json.dump(report, f, indent=2, default=str)
                logger.info(f"Report saved to {save_path}")
            except Exception as e:
                logger.error(f"Error saving report: {e}")
        return report
    
    def _generate_parameter_combinations(self, parameter_ranges: Dict[str, List]) -> List[Dict]:
        """매개변수 조합 생성"""
        import itertools
        keys, values = list(parameter_ranges.keys()), list(parameter_ranges.values())
        return [dict(zip(keys, c)) for c in itertools.product(*values)]
    
    def _create_optimization_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """최적화 결과 요약"""
        if not results: return {}
        return {
            'best_sharpe_ratio': max(results, key=lambda x: x['sharpe_ratio']),
            'total_combinations_tested': len(results)
        }
    
    def _create_walk_forward_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """워크 포워드 분석 요약"""
        if not results: return {}
        returns = [r['test_return_percent'] for r in results]
        return {
            'total_periods': len(results),
            'average_return_percent': sum(returns) / len(returns),
            'positive_periods': len([r for r in returns if r > 0])
        }
    
    def _create_strategy_comparison(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """전략 비교 분석"""
        if not strategy_results: return {}
        summaries = {name: data['summary'] for name, data in strategy_results.items()}
        rankings = {'sharpe_ratio': sorted(summaries.items(), key=lambda x: x[1]['sharpe_ratio'], reverse=True)}
        return {'rankings': rankings, 'best_overall': rankings['sharpe_ratio'][0][0] if rankings['sharpe_ratio'] else None}
 