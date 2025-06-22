from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import json

from infrastructure.logging import get_logger
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository

from ..engine.backtesting_engine import BacktestingEngine
from ..models.backtest_result import BacktestResult

logger = get_logger(__name__)


class BacktestingService:
    """백테스팅 서비스 - 고수준 백테스팅 기능 제공"""
    
    def __init__(self, 
                 stock_repository: Optional[StockRepository] = None):
        """
        Args:
            stock_repository: 주식 데이터 저장소 (선택적)
        """
        self.stock_repository = stock_repository or SQLStockRepository()
        self.stock_analysis_service = StockAnalysisService(self.stock_repository)
        
        logger.info("BacktestingService initialized")
    
    def run_strategy_backtest(self,
                            tickers: List[str],
                            start_date: datetime,
                            end_date: datetime,
                            initial_capital: float = 100000.0,
                            commission_rate: float = 0.001,
                            risk_per_trade: float = 0.02,
                            data_interval: str = '1h') -> BacktestResult:
        """
        전략 백테스트 실행
        
        Args:
            tickers: 백테스트할 종목 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_capital: 초기 자본금
            commission_rate: 수수료율
            risk_per_trade: 거래당 리스크 비율
            data_interval: 데이터 간격
        """
        logger.info(f"Starting strategy backtest for {len(tickers)} tickers")
        
        # 백테스팅 엔진 초기화
        engine = BacktestingEngine(
            stock_analysis_service=self.stock_analysis_service,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            risk_per_trade=risk_per_trade
        )
        
        # 백테스트 실행
        result = engine.run_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            data_interval=data_interval
        )
        
        logger.info(f"Backtest completed. Return: {result.total_return_percent:.2f}%, "
                   f"Win Rate: {result.win_rate:.1%}")
        
        return result
    
    def run_parameter_optimization(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 parameter_ranges: Dict[str, List],
                                 initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        매개변수 최적화 백테스트
        
        Args:
            tickers: 백테스트할 종목 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            parameter_ranges: 최적화할 매개변수 범위
            initial_capital: 초기 자본금
        """
        logger.info("Starting parameter optimization backtest")
        
        optimization_results = []
        best_result = None
        best_return = float('-inf')
        
        # 매개변수 조합 생성
        param_combinations = self._generate_parameter_combinations(parameter_ranges)
        
        for i, params in enumerate(param_combinations):
            logger.info(f"Testing parameter set {i+1}/{len(param_combinations)}: {params}")
            
            try:
                result = self.run_strategy_backtest(
                    tickers=tickers,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    commission_rate=params.get('commission_rate', 0.001),
                    risk_per_trade=params.get('risk_per_trade', 0.02),
                    data_interval=params.get('data_interval', '1h')
                )
                
                result_summary = {
                    'parameters': params,
                    'total_return_percent': result.total_return_percent,
                    'annualized_return_percent': result.annualized_return_percent,
                    'max_drawdown_percent': result.max_drawdown_percent,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades,
                    'profit_factor': result.profit_factor
                }
                
                optimization_results.append(result_summary)
                
                # 최적 결과 업데이트 (샤프 비율 기준)
                if result.sharpe_ratio > best_return:
                    best_return = result.sharpe_ratio
                    best_result = result_summary
                    
            except Exception as e:
                logger.error(f"Error in parameter optimization for {params}: {e}")
                continue
        
        return {
            'best_parameters': best_result,
            'all_results': optimization_results,
            'optimization_summary': self._create_optimization_summary(optimization_results)
        }
    
    def run_walk_forward_analysis(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                train_period_months: int = 6,
                                test_period_months: int = 1,
                                initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        워크 포워드 분석 (시간 순서대로 학습/테스트 반복)
        
        Args:
            tickers: 백테스트할 종목 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            train_period_months: 학습 기간 (월)
            test_period_months: 테스트 기간 (월)
            initial_capital: 초기 자본금
        """
        logger.info("Starting walk forward analysis")
        
        walk_forward_results = []
        current_date = start_date
        
        while current_date < end_date:
            train_start = current_date
            train_end = current_date + timedelta(days=train_period_months * 30)
            test_start = train_end
            test_end = test_start + timedelta(days=test_period_months * 30)
            
            if test_end > end_date:
                test_end = end_date
            
            logger.info(f"Training: {train_start} to {train_end}, Testing: {test_start} to {test_end}")
            
            try:
                # 테스트 기간 백테스트 실행
                test_result = self.run_strategy_backtest(
                    tickers=tickers,
                    start_date=test_start,
                    end_date=test_end,
                    initial_capital=initial_capital
                )
                
                period_result = {
                    'train_period': {'start': train_start, 'end': train_end},
                    'test_period': {'start': test_start, 'end': test_end},
                    'test_return_percent': test_result.total_return_percent,
                    'test_max_drawdown_percent': test_result.max_drawdown_percent,
                    'test_win_rate': test_result.win_rate,
                    'test_total_trades': test_result.total_trades
                }
                
                walk_forward_results.append(period_result)
                
            except Exception as e:
                logger.error(f"Error in walk forward period {train_start} to {test_end}: {e}")
                continue
            
            # 다음 기간으로 이동
            current_date = test_start
        
        return {
            'periods': walk_forward_results,
            'summary': self._create_walk_forward_summary(walk_forward_results)
        }
    
    def compare_strategies(self,
                         tickers: List[str],
                         start_date: datetime,
                         end_date: datetime,
                         strategy_configs: Dict[str, Dict],
                         initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        다중 전략 비교 백테스트
        
        Args:
            tickers: 백테스트할 종목 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy_configs: 전략별 설정 (전략명 -> 설정 딕셔너리)
            initial_capital: 초기 자본금
        """
        logger.info(f"Comparing {len(strategy_configs)} strategies")
        
        strategy_results = {}
        
        for strategy_name, config in strategy_configs.items():
            logger.info(f"Testing strategy: {strategy_name}")
            
            try:
                result = self.run_strategy_backtest(
                    tickers=tickers,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    commission_rate=config.get('commission_rate', 0.001),
                    risk_per_trade=config.get('risk_per_trade', 0.02),
                    data_interval=config.get('data_interval', '1h')
                )
                
                strategy_results[strategy_name] = {
                    'config': config,
                    'result': result,
                    'summary': {
                        'total_return_percent': result.total_return_percent,
                        'annualized_return_percent': result.annualized_return_percent,
                        'max_drawdown_percent': result.max_drawdown_percent,
                        'sharpe_ratio': result.sharpe_ratio,
                        'win_rate': result.win_rate,
                        'total_trades': result.total_trades,
                        'profit_factor': result.profit_factor
                    }
                }
                
            except Exception as e:
                logger.error(f"Error testing strategy {strategy_name}: {e}")
                continue
        
        return {
            'strategies': strategy_results,
            'comparison': self._create_strategy_comparison(strategy_results)
        }
    
    def generate_report(self, result: BacktestResult, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        백테스트 결과 리포트 생성
        
        Args:
            result: 백테스트 결과
            save_path: 저장 경로 (선택적)
        """
        logger.info("Generating backtest report")
        
        report = {
            'executive_summary': {
                'backtest_period': f"{result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}",
                'total_return': f"{result.total_return_percent:.2f}%",
                'annualized_return': f"{result.annualized_return_percent:.2f}%",
                'max_drawdown': f"{result.max_drawdown_percent:.2f}%",
                'sharpe_ratio': f"{result.sharpe_ratio:.2f}",
                'win_rate': f"{result.win_rate:.1%}",
                'total_trades': result.total_trades
            },
            'detailed_metrics': result.to_dict(),
            'trade_analysis': {
                'signal_strength': result.analyze_by_signal_strength(),
                'market_conditions': result.analyze_by_market_condition(),
                'holding_periods': result.analyze_by_holding_period()
            },
            'monthly_performance': result.get_monthly_performance().to_dict('records') if not result.get_monthly_performance().empty else []
        }
        
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                logger.info(f"Report saved to {save_path}")
            except Exception as e:
                logger.error(f"Error saving report: {e}")
        
        return report
    
    def _generate_parameter_combinations(self, parameter_ranges: Dict[str, List]) -> List[Dict]:
        """매개변수 조합 생성"""
        import itertools
        
        keys = list(parameter_ranges.keys())
        values = list(parameter_ranges.values())
        
        combinations = []
        for combination in itertools.product(*values):
            param_dict = dict(zip(keys, combination))
            combinations.append(param_dict)
        
        return combinations
    
    def _create_optimization_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """최적화 결과 요약"""
        if not results:
            return {}
        
        # 성과 지표별 최고 결과
        best_return = max(results, key=lambda x: x['total_return_percent'])
        best_sharpe = max(results, key=lambda x: x['sharpe_ratio'])
        best_win_rate = max(results, key=lambda x: x['win_rate'])
        min_drawdown = min(results, key=lambda x: x['max_drawdown_percent'])
        
        return {
            'best_total_return': best_return,
            'best_sharpe_ratio': best_sharpe,
            'best_win_rate': best_win_rate,
            'minimum_drawdown': min_drawdown,
            'total_combinations_tested': len(results)
        }
    
    def _create_walk_forward_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """워크 포워드 분석 요약"""
        if not results:
            return {}
        
        returns = [r['test_return_percent'] for r in results]
        win_rates = [r['test_win_rate'] for r in results]
        
        return {
            'total_periods': len(results),
            'average_return_percent': sum(returns) / len(returns),
            'average_win_rate': sum(win_rates) / len(win_rates),
            'positive_periods': len([r for r in returns if r > 0]),
            'consistency_score': len([r for r in returns if r > 0]) / len(returns)
        }
    
    def _create_strategy_comparison(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """전략 비교 분석"""
        if not strategy_results:
            return {}
        
        summaries = {name: data['summary'] for name, data in strategy_results.items()}
        
        # 각 지표별 순위
        rankings = {}
        metrics = ['total_return_percent', 'sharpe_ratio', 'win_rate', 'profit_factor']
        
        for metric in metrics:
            sorted_strategies = sorted(summaries.items(), 
                                     key=lambda x: x[1][metric], 
                                     reverse=True)
            rankings[metric] = [name for name, _ in sorted_strategies]
        
        # 최대 낙폭은 낮을수록 좋음
        sorted_drawdown = sorted(summaries.items(), 
                               key=lambda x: x[1]['max_drawdown_percent'])
        rankings['max_drawdown_percent'] = [name for name, _ in sorted_drawdown]
        
        return {
            'rankings': rankings,
            'best_overall': rankings['sharpe_ratio'][0] if rankings['sharpe_ratio'] else None,
            'strategy_count': len(strategy_results)
        } 