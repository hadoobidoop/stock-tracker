#!/usr/bin/env python3
"""
백테스팅 실행 스크립트

이 스크립트는 기존 신호 감지 전략을 사용하여 백테스팅을 실행합니다.
모든 매수매도 전략이 완전히 재현됩니다.

사용 예시:
python run_backtest.py --tickers AAPL MSFT NVDA --start-date 2023-01-01 --end-date 2024-01-01
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import get_logger
from domain.backtesting.service.backtesting_service import BacktestingService

logger = get_logger(__name__)


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='백테스팅 실행 스크립트')
    
    # 필수 인수
    parser.add_argument('--tickers', nargs='+', required=True,
                       help='백테스트할 종목 리스트 (예: AAPL MSFT NVDA)')
    
    parser.add_argument('--start-date', required=True,
                       help='백테스트 시작 날짜 (YYYY-MM-DD)')
    
    parser.add_argument('--end-date', required=True,
                       help='백테스트 종료 날짜 (YYYY-MM-DD)')
    
    # 선택적 인수
    parser.add_argument('--initial-capital', type=float, default=100000.0,
                       help='초기 자본금 (기본값: 100000)')
    
    parser.add_argument('--commission-rate', type=float, default=0.001,
                       help='수수료율 (기본값: 0.001 = 0.1%%)')
    
    parser.add_argument('--risk-per-trade', type=float, default=0.02,
                       help='거래당 리스크 비율 (기본값: 0.02 = 2%%)')
    
    parser.add_argument('--data-interval', default='1h',
                       choices=['1h', '1d'],
                       help='데이터 간격 (기본값: 1h)')
    
    parser.add_argument('--output-dir', default='./backtest_results',
                       help='결과 저장 디렉토리 (기본값: ./backtest_results)')
    
    parser.add_argument('--mode', default='single',
                       choices=['single', 'optimization', 'walk-forward', 'comparison'],
                       help='실행 모드 (기본값: single)')
    
    return parser.parse_args()


def run_single_backtest(service: BacktestingService, args):
    """단일 백테스트 실행"""
    logger.info("=== 단일 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    result = service.run_strategy_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval
    )
    
    # 결과 출력
    print("\n" + "="*60)
    print("백테스트 결과 요약")
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
    
    # 상세 리포트 생성 및 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f"backtest_report_{timestamp}.json"
    
    report = service.generate_report(result, str(report_path))
    
    print(f"\n상세 리포트가 저장되었습니다: {report_path}")
    
    return result


def run_parameter_optimization(service: BacktestingService, args):
    """매개변수 최적화 백테스트"""
    logger.info("=== 매개변수 최적화 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 최적화할 매개변수 범위 정의
    parameter_ranges = {
        'commission_rate': [0.0005, 0.001, 0.002],
        'risk_per_trade': [0.01, 0.02, 0.03],
        'data_interval': ['1h', '1d']
    }
    
    optimization_result = service.run_parameter_optimization(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        parameter_ranges=parameter_ranges,
        initial_capital=args.initial_capital
    )
    
    # 최적 결과 출력
    best = optimization_result['best_parameters']
    if best:
        print("\n" + "="*60)
        print("최적 매개변수 (샤프 비율 기준)")
        print("="*60)
        print(f"매개변수: {best['parameters']}")
        print(f"총 수익률: {best['total_return_percent']:.2f}%")
        print(f"샤프 비율: {best['sharpe_ratio']:.2f}")
        print(f"승률: {best['win_rate']:.1%}")
        print("="*60)
    
    # 결과 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = output_dir / f"optimization_result_{timestamp}.json"
    
    import json
    with open(result_path, 'w') as f:
        json.dump(optimization_result, f, indent=2, default=str)
    
    print(f"\n최적화 결과가 저장되었습니다: {result_path}")
    
    return optimization_result


def run_walk_forward_analysis(service: BacktestingService, args):
    """워크 포워드 분석"""
    logger.info("=== 워크 포워드 분석 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    walk_forward_result = service.run_walk_forward_analysis(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        train_period_months=6,
        test_period_months=1,
        initial_capital=args.initial_capital
    )
    
    # 결과 출력
    summary = walk_forward_result['summary']
    print("\n" + "="*60)
    print("워크 포워드 분석 결과")
    print("="*60)
    print(f"총 기간 수: {summary['total_periods']}")
    print(f"평균 수익률: {summary['average_return_percent']:.2f}%")
    print(f"평균 승률: {summary['average_win_rate']:.1%}")
    print(f"수익 기간: {summary['positive_periods']}/{summary['total_periods']}")
    print(f"일관성 점수: {summary['consistency_score']:.1%}")
    print("="*60)
    
    # 결과 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = output_dir / f"walk_forward_result_{timestamp}.json"
    
    import json
    with open(result_path, 'w') as f:
        json.dump(walk_forward_result, f, indent=2, default=str)
    
    print(f"\n워크 포워드 분석 결과가 저장되었습니다: {result_path}")
    
    return walk_forward_result


def run_strategy_comparison(service: BacktestingService, args):
    """전략 비교 분석"""
    logger.info("=== 전략 비교 분석 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 서로 다른 전략 설정 정의
    strategy_configs = {
        '보수적 전략': {
            'commission_rate': 0.001,
            'risk_per_trade': 0.01,  # 1% 리스크
            'data_interval': '1d'
        },
        '기본 전략': {
            'commission_rate': 0.001,
            'risk_per_trade': 0.02,  # 2% 리스크
            'data_interval': '1h'
        },
        '공격적 전략': {
            'commission_rate': 0.001,
            'risk_per_trade': 0.03,  # 3% 리스크
            'data_interval': '1h'
        }
    }
    
    comparison_result = service.compare_strategies(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        strategy_configs=strategy_configs,
        initial_capital=args.initial_capital
    )
    
    # 결과 출력
    print("\n" + "="*60)
    print("전략 비교 결과")
    print("="*60)
    
    for strategy_name, data in comparison_result['strategies'].items():
        summary = data['summary']
        print(f"\n{strategy_name}:")
        print(f"  총 수익률: {summary['total_return_percent']:.2f}%")
        print(f"  샤프 비율: {summary['sharpe_ratio']:.2f}")
        print(f"  최대 낙폭: {summary['max_drawdown_percent']:.2f}%")
        print(f"  승률: {summary['win_rate']:.1%}")
        print(f"  총 거래: {summary['total_trades']}")
    
    comparison = comparison_result['comparison']
    if comparison.get('best_overall'):
        print(f"\n최고 전략 (샤프 비율 기준): {comparison['best_overall']}")
    
    print("="*60)
    
    # 결과 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = output_dir / f"strategy_comparison_{timestamp}.json"
    
    # 결과를 JSON 직렬화 가능하도록 변환
    serializable_result = {}
    for strategy_name, data in comparison_result['strategies'].items():
        serializable_result[strategy_name] = {
            'config': data['config'],
            'summary': data['summary']
        }
    
    final_result = {
        'strategies': serializable_result,
        'comparison': comparison_result['comparison']
    }
    
    import json
    with open(result_path, 'w') as f:
        json.dump(final_result, f, indent=2, default=str)
    
    print(f"\n전략 비교 결과가 저장되었습니다: {result_path}")
    
    return comparison_result


def main():
    """메인 함수"""
    args = parse_arguments()
    
    try:
        # 백테스팅 서비스 초기화
        logger.info("백테스팅 서비스 초기화 중...")
        service = BacktestingService()
        
        # 모드에 따른 실행
        if args.mode == 'single':
            run_single_backtest(service, args)
        elif args.mode == 'optimization':
            run_parameter_optimization(service, args)
        elif args.mode == 'walk-forward':
            run_walk_forward_analysis(service, args)
        elif args.mode == 'comparison':
            run_strategy_comparison(service, args)
        
        logger.info("백테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 