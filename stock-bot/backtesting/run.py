#!/usr/bin/env python3
"""
Backtesting Run Script

YAML 전략을 지정하여 백테스팅을 실행하는 독립적인 진입점
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtesting.service.backtesting_service import BacktestingService
from infrastructure.logging import get_logger

logger = get_logger(__name__)


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='Run backtesting for YAML strategies')
    
    # 필수 인수
    parser.add_argument('--strategy', required=True, 
                       help='YAML strategy name (e.g., conservative, aggressive)')
    parser.add_argument('--tickers', required=True, nargs='+',
                       help='Stock tickers to test (e.g., AAPL TSLA)')
    parser.add_argument('--start-date', required=True, type=str,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, type=str,
                       help='End date (YYYY-MM-DD)')
    
    # 선택적 인수
    parser.add_argument('--initial-capital', type=float, default=100000.0,
                       help='Initial capital (default: 100000)')
    parser.add_argument('--commission-rate', type=float, default=0.001,
                       help='Commission rate (default: 0.001)')
    parser.add_argument('--risk-per-trade', type=float, default=0.02,
                       help='Risk per trade (default: 0.02)')
    parser.add_argument('--data-interval', default='1d',
                       help='Data interval (default: 1d)')
    parser.add_argument('--compare', nargs='+',
                       help='Compare multiple strategies (e.g., --compare conservative aggressive)')
    parser.add_argument('--definitions-path', type=str,
                       help='Custom path to strategy definitions directory')
    parser.add_argument('--save-report', type=str,
                       help='Path to save detailed report')
    
    return parser.parse_args()


def validate_date(date_string: str) -> datetime:
    """날짜 문자열 검증 및 변환"""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Use YYYY-MM-DD format.")


def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    try:
        # 날짜 검증
        start_date = validate_date(args.start_date)
        end_date = validate_date(args.end_date)
        
        if start_date >= end_date:
            raise ValueError("Start date must be before end date")
        
        # 전략 정의 경로 설정
        definitions_path = None
        if args.definitions_path:
            definitions_path = Path(args.definitions_path)
            if not definitions_path.exists():
                raise FileNotFoundError(f"Strategy definitions path not found: {definitions_path}")
        
        # BacktestingService 초기화
        logger.info("Initializing BacktestingService...")
        service = BacktestingService(strategy_definitions_path=definitions_path)
        
        # 공통 백테스트 파라미터
        backtest_params = {
            'tickers': args.tickers,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': args.initial_capital,
            'commission_rate': args.commission_rate,
            'risk_per_trade': args.risk_per_trade,
            'data_interval': args.data_interval
        }
        
        # 비교 모드인지 단일 분석 모드인지 확인
        if args.compare:
            # 다중 전략 비교
            logger.info(f"Running comparison for strategies: {args.compare}")
            result = service.run_comparison(args.compare, **backtest_params)
            
            # 결과 출력
            print("\\n" + "="*80)
            print("STRATEGY COMPARISON RESULTS")
            print("="*80)
            
            comparison_summary = result.get('comparison_summary', {})
            print(f"Best Strategy: {comparison_summary.get('best_strategy', 'N/A')}")
            print(f"Strategies Tested: {comparison_summary.get('strategies_tested', 0)}")
            print(f"Period: {comparison_summary.get('comparison_period', 'N/A')}")
            
            print("\\nRanking by Sharpe Ratio:")
            for i, (name, sharpe) in enumerate(comparison_summary.get('ranking_by_sharpe', [])[:5], 1):
                print(f"  {i}. {name}: {sharpe:.3f}")
            
            print("\\nRanking by Total Return:")
            for i, (name, return_pct) in enumerate(comparison_summary.get('ranking_by_return', [])[:5], 1):
                print(f"  {i}. {name}: {return_pct:.2f}%")
            
        else:
            # 단일 전략 분석
            logger.info(f"Running analysis for strategy: {args.strategy}")
            result = service.run_single_analysis(args.strategy, **backtest_params)
            
            # 결과 출력
            print("\\n" + "="*80)
            print(f"BACKTEST RESULTS - {args.strategy.upper()} STRATEGY")
            print("="*80)
            print(f"Period: {args.start_date} to {args.end_date}")
            print(f"Tickers: {', '.join(args.tickers)}")
            print(f"Initial Capital: ${args.initial_capital:,.2f}")
            print("-"*40)
            print(f"Total Return: {result.total_return_percent:.2f}%")
            print(f"Annualized Return: {result.annualized_return_percent:.2f}%")
            print(f"Max Drawdown: {result.max_drawdown_percent:.2f}%")
            print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
            print(f"Win Rate: {result.win_rate:.2f}%")
            print(f"Total Trades: {result.total_trades}")
            print(f"Profit Factor: {result.profit_factor:.2f}")
            print(f"Final Capital: ${result.final_capital:,.2f}")
            
            # 월별 성과가 있으면 표시
            monthly_perf = result.get_monthly_performance()
            if not monthly_perf.empty:
                print("\\nMonthly Performance (Last 12 months):")
                recent_months = monthly_perf.tail(12)
                for _, row in recent_months.iterrows():
                    print(f"  {row.name}: {row['return_percent']:.2f}%")
        
        # 상세 리포트 저장
        if args.save_report:
            if args.compare:
                # 비교 리포트 저장
                import json
                with open(args.save_report, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                logger.info(f"Comparison report saved to {args.save_report}")
            else:
                # 단일 전략 리포트 저장
                service.generate_report(result, args.save_report)
        
        print("\\nBacktest completed successfully!")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()