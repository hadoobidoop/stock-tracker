#!/usr/bin/env python3
"""
백테스팅 실행 스크립트 - 다중 전략 시스템 지원

이 스크립트는 새로운 다중 전략 시스템을 활용하여 다양한 백테스팅을 실행합니다.

새로운 기능:
1. 특정 전략으로 백테스팅
2. 전략 조합으로 백테스팅  
3. 자동 전략 선택 백테스팅
4. 전략 비교 백테스팅
5. 기존 Static Strategy Mix 방식 지원

사용 예시:
# 특정 전략으로 백테스팅
python run_backtest.py --tickers AAPL MSFT NVDA --start-date 2023-01-01 --end-date 2024-01-01 --mode strategy --strategy AGGRESSIVE

# 전략 비교
python run_backtest.py --tickers AAPL MSFT NVDA --start-date 2023-01-01 --end-date 2024-01-01 --mode strategy-comparison

# 전략 조합
python run_backtest.py --tickers AAPL MSFT NVDA --start-date 2023-01-01 --end-date 2024-01-01 --mode strategy-mix --strategy-mix balanced_mix

# 자동 전략 선택
python run_backtest.py --tickers AAPL MSFT NVDA --start-date 2023-01-01 --end-date 2024-01-01 --mode auto-strategy
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import get_logger
from domain.backtesting.service.backtesting_service import BacktestingService
from domain.signals.models.enums import StrategyType
from domain.orchestration.strategy_orchestrator import StrategyOrchestrator

# 거시지표 분석 기능 추가

logger = get_logger(__name__)


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='Stock-Bot 백테스팅 실행 스크립트. 단일 전략 분석 또는 다중 전략 비교를 수행합니다.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 기본 백테스팅 설정
    parser.add_argument('--tickers', required=True, nargs='+', help='백테스트할 종목 리스트 (예: AAPL MSFT)')
    parser.add_argument('--start-date', required=True, help='백테스트 시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='백테스트 종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--initial-capital', type=float, default=100000, help='초기 자본금 (기본값: 100,000)')
    parser.add_argument('--commission-rate', type=float, default=0.001, help='수수료율 (기본값: 0.001)')
    parser.add_argument('--risk-per-trade', type=float, default=0.02, help='거래당 리스크 비율 (기본값: 0.02)')
    parser.add_argument('--data-interval', default='1h', choices=['1h', '1d'], help='데이터 간격 (기본값: 1h)')
    parser.add_argument('--output-dir', default='./backtest_results', help='결과 저장 디렉토리')

    # 실행 모드를 결정하는 핵심 인자 그룹 (둘 중 하나는 필수)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--strategy', metavar='STRATEGY_NAME',
                            help='단일 전략의 성과를 심층 분석합니다.')
    mode_group.add_argument('--compare', nargs='+', metavar='STRATEGY_NAME',
                            help='여러 전략들의 성과를 비교 분석합니다.')

    return parser.parse_args()


def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    try:
        logger.info("백테스팅 서비스 초기화 중...")
        service = BacktestingService()
        
        # 공통 인자 준비
        common_kwargs = {
            "tickers": args.tickers,
            "start_date": datetime.strptime(args.start_date, '%Y-%m-%d'),
            "end_date": datetime.strptime(args.end_date, '%Y-%m-%d'),
            "initial_capital": args.initial_capital,
            "commission_rate": args.commission_rate,
            "risk_per_trade": args.risk_per_trade,
            "data_interval": args.data_interval,
        }

        if args.compare:
            logger.info(f"=== 여러 전략 비교 분석 모드: {', '.join(args.compare)} ===")
            result = service.run_comparison(strategies=args.compare, **common_kwargs)
            print_strategy_comparison_results(result)
            save_strategy_comparison_results(result, args)

        elif args.strategy:
            logger.info(f"=== {args.strategy} 단일 전략 심층 분석 모드 ===")
            result = service.run_single_analysis(strategy_name=args.strategy, **common_kwargs)
            print_backtest_summary(result, f"{args.strategy} 전략 백테스트")
            save_backtest_report(service, result, args, f"strategy_{args.strategy}_backtest")

        logger.info("백테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


def print_backtest_summary(result, title):
    """백테스트 결과 요약 출력"""
    print("\n" + "="*60)
    print(f"{title} 결과 요약")
    print("="*60)
    print(f"기간: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}")
    print(f"초기 자본: ${result.initial_capital:,.2f}")
    print(f"최종 자본: ${result.final_capital:,.2f}")
    print(f"총 수익률: {result.total_return_percent:.2f}%")
    print(f"연환산 수익률: {result.annualized_return_percent:.2f}%")
    print(f"최대 낙폭: {result.max_drawdown_percent:.2f}%")
    print(f"샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"총 거래 수: {result.total_trades}")
    print(f"승률: {result.win_rate:.1%}")
    print(f"수익 팩터: {result.profit_factor:.2f}")
    print("="*60)


def print_strategy_comparison_results(comparison_result):
    """전략 비교 결과 출력"""
    summary = comparison_result['comparison_summary']
    analysis = comparison_result['strategy_analysis']
    
    print("\n" + "="*80)
    print("전략 비교 결과")
    print("="*80)
    print(f"테스트 기간: {summary['comparison_period']}")
    print(f"비교 전략 수: {summary['strategies_tested']}")
    print(f"최고 전략 (샤프 비율): {summary['best_strategy']}")
    
    print("\n📊 전략별 성과 요약:")
    print("-" * 80)
    print(f"{'전략명':<30} {'수익률':<12} {'샤프비율':<12} {'승률':<8} {'최대낙폭':<12} {'거래수':<8}")
    print("-" * 80)
    
    for strategy_name, data in analysis.items():
        print(f"{strategy_name:<30} "
              f"{data['total_return_percent']:>10.2f}% "
              f"{data['sharpe_ratio']:>10.2f} "
              f"{data['win_rate']:>6.1%} "
              f"{data['max_drawdown_percent']:>10.2f}% "
              f"{data['total_trades']:>6}")
    
    print("\n🏆 순위 (샤프 비율 기준):")
    for i, (strategy, sharpe) in enumerate(summary['ranking_by_sharpe'], 1):
        print(f"{i}. {strategy}: {sharpe:.2f}")
    
    print("\n💰 순위 (총 수익률 기준):")
    for i, (strategy, return_pct) in enumerate(summary['ranking_by_return'], 1):
        print(f"{i}. {strategy}: {return_pct:.2f}%")
    
    print("="*80)


def save_backtest_report(service: BacktestingService, result, args, prefix):
    """백테스트 리포트 저장"""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f"{prefix}_{timestamp}.json"
    
    report = service.generate_report(result, str(report_path))
    
    print(f"\n상세 리포트가 저장되었습니다: {report_path}")


def save_strategy_comparison_results(comparison_result, args):
    """전략 비교 결과 저장"""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = output_dir / f"strategy_comparison_{timestamp}.json"
    
    # BacktestResult 객체를 직렬화 가능한 딕셔너리로 변환
    serializable_results = {
        name: res.to_dict() for name, res in comparison_result['strategy_results'].items()
    }
    comparison_result['strategy_results'] = serializable_results
    
    import json
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(comparison_result, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n전략 비교 결과가 저장되었습니다: {result_path}")


if __name__ == '__main__':
    from infrastructure.logging import setup_logging
    setup_logging(log_level='DEBUG')
    main() 