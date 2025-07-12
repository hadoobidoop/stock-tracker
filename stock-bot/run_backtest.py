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
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import get_logger
from domain.backtesting.service.backtesting_service import BacktestingService
from domain.analysis.config.static_strategies import StrategyType

# 거시지표 분석 기능 추가
from domain.analysis.utils.market_indicators import get_market_indicator_analysis

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
            "data_interval": args.data_interval,
        }

        if args.compare:
            logger.info(f"=== 여러 전략 비교 분석 모드: {', '.join(args.compare)} ===")
            # TODO: BacktestingService에 compare_strategies 구현 필요
            # comparison_result = service.compare_strategies(strategies=args.compare, **common_kwargs)
            # print_strategy_comparison_results(comparison_result)
            # save_strategy_comparison_results(comparison_result, args)
            pass # 임시 구현

        elif args.strategy:
            logger.info(f"=== {args.strategy} 단일 전략 심층 분석 모드 ===")
            # TODO: BacktestingService에 run_single_strategy 구현 필요
            # result = service.run_single_strategy(strategy_name=args.strategy, **common_kwargs)
            # print_backtest_summary(result, f"{args.strategy} 전략 백테스트")
            # save_backtest_report(service, result, args, f"strategy_{args.strategy}_backtest")
            pass # 임시 구현

        logger.info("백테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 