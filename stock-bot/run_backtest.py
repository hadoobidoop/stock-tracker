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
    parser = argparse.ArgumentParser(description='다중 전략 백테스팅 실행 스크립트')
    
    # 기본 백테스팅 설정
    parser.add_argument('--tickers', required=True, nargs='+',
                       help='백테스트할 종목 리스트 (예: AAPL MSFT NVDA)')
    
    parser.add_argument('--start-date', required=True,
                       help='백테스트 시작 날짜 (YYYY-MM-DD)')
    
    parser.add_argument('--end-date', required=True,
                       help='백테스트 종료 날짜 (YYYY-MM-DD)')
    
    parser.add_argument('--initial-capital', type=float, default=100000,
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
                       choices=['single', 'strategy', 'strategy-mix', 'auto-strategy', 
                               'strategy-comparison', 'dynamic-strategy', 'dynamic-comparison',
                               'optimization', 'walk-forward', 'comparison', 'macro-analysis'],
                       help='실행 모드 (기본값: single)')
    
    # 동적으로 사용 가능한 전략 목록 가져오기
    try:
        from common.config.settings import get_available_static_strategies, get_available_dynamic_strategies, get_available_strategy_mix
        
        available_static = get_available_static_strategies()
        available_dynamic = get_available_dynamic_strategies()
        available_mix = get_available_strategy_mix()
        
    except ImportError:
        # 폴백: 기본 전략들
        available_static = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE']
        available_dynamic = ['dynamic_weight_strategy']
        available_mix = ['balanced_mix', 'conservative_mix', 'aggressive_mix']
    
    # 정적 전략 관련 인수들
    parser.add_argument('--strategy', 
                       choices=available_static,
                       help='사용할 정적 전략 (기본 3가지 + 확장 전략 포함, strategy 모드에서 필수)')
    
    parser.add_argument('--strategy-mix',
                       choices=available_mix,
                       help='사용할 전략 조합 (strategy-mix 모드에서 필수)')
    
    parser.add_argument('--compare-strategies', nargs='+',
                       choices=available_static,
                       help='비교할 전략들 (지정하지 않으면 모든 전략 비교)')
    
    # 동적 전략 관련 인수들
    parser.add_argument('--dynamic-strategy',
                       choices=available_dynamic,
                       help='사용할 동적 전략 (dynamic-strategy 모드에서 필수)')
    
    parser.add_argument('--compare-dynamic-strategies', nargs='+',
                       choices=available_dynamic,
                       help='비교할 동적 전략들 (dynamic-comparison 모드에서 사용)')
    
    parser.add_argument('--use-static-mix', action='store_true',
                        help='Static Strategy Mix 신호 감지 시스템 사용')
    
    return parser.parse_args()


def run_single_backtest(service: BacktestingService, args):
    """단일 백테스트 실행 (기존 호환성)"""
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
        data_interval=args.data_interval,
        use_enhanced_signals=not args.use_static_mix
    )
    
    # 결과 출력
    print_backtest_summary(result, "단일 백테스트")
    
    # 상세 리포트 생성 및 저장
    save_backtest_report(service, result, args, "single_backtest")
    
    return result


def run_strategy_backtest(service: BacktestingService, args):
    """특정 전략으로 백테스트 실행"""
    if not args.strategy:
        raise ValueError("--strategy 인수가 필요합니다.")
    
    logger.info(f"=== {args.strategy} 전략 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    strategy_type = StrategyType[args.strategy]
    
    result = service.run_specific_strategy_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        strategy_type=strategy_type,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval
    )
    
    # 결과 출력
    print_backtest_summary(result, f"{args.strategy} 전략 백테스트")
    
    # 상세 리포트 생성 및 저장
    save_backtest_report(service, result, args, f"strategy_{args.strategy.lower()}_backtest")
    
    return result


def run_strategy_mix_backtest(service: BacktestingService, args):
    """Static Strategy Mix로 백테스트 실행"""
    if not args.strategy_mix:
        raise ValueError("--strategy-mix 인수가 필요합니다.")
    
    logger.info(f"=== {args.strategy_mix} Static Strategy Mix 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    result = service.run_strategy_mix_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        mix_name=args.strategy_mix,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval
    )
    
    # 결과 출력
    print_backtest_summary(result, f"{args.strategy_mix} Static Strategy Mix 백테스트")
    
    # 상세 리포트 생성 및 저장
    save_backtest_report(service, result, args, f"strategy_mix_{args.strategy_mix}_backtest")
    
    return result


def run_auto_strategy_backtest(service: BacktestingService, args):
    """자동 전략 선택으로 백테스트 실행"""
    logger.info("=== 자동 전략 선택 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    result = service.run_auto_strategy_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval
    )
    
    # 결과 출력
    print_backtest_summary(result, "자동 전략 선택 백테스트")
    
    # 상세 리포트 생성 및 저장
    save_backtest_report(service, result, args, "auto_strategy_backtest")
    
    return result


def run_strategy_comparison(service: BacktestingService, args):
    """전략 비교 백테스트 실행"""
    logger.info("=== 전략 비교 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 비교할 전략들 결정
    strategies = None
    if args.compare_strategies:
        strategies = [StrategyType[s] for s in args.compare_strategies]
    
    comparison_result = service.compare_all_strategies(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval,
        strategies=strategies
    )
    
    # 결과 출력
    print_strategy_comparison_results(comparison_result)
    
    # 결과 저장
    save_strategy_comparison_results(comparison_result, args)
    
    return comparison_result


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
    
    # 전략 정보 출력
    strategy_info = result.backtest_settings
    if strategy_info.get('strategy_type'):
        print(f"사용 전략: {strategy_info['strategy_type']}")
    if strategy_info.get('strategy_mix'):
        print(f"전략 조합: {strategy_info['strategy_mix']}")
    if strategy_info.get('auto_strategy_selection'):
        print("자동 전략 선택: 활성화")
    
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
    print(f"{'전략명':<15} {'수익률':<10} {'샤프비율':<10} {'승률':<8} {'최대낙폭':<10} {'거래수':<8}")
    print("-" * 80)
    
    for strategy_name, data in analysis.items():
        print(f"{strategy_name:<15} "
              f"{data['total_return_percent']:>7.2f}% "
              f"{data['sharpe_ratio']:>9.2f} "
              f"{data['win_rate']:>6.1%} "
              f"{data['max_drawdown_percent']:>8.2f}% "
              f"{data['total_trades']:>7}")
    
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
    
    # 결과를 JSON 직렬화 가능하도록 변환
    serializable_result = {
        'strategy_analysis': comparison_result['strategy_analysis'],
        'comparison_summary': comparison_result['comparison_summary']
    }
    
    import json
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_result, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n전략 비교 결과가 저장되었습니다: {result_path}")


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


def run_static_mix_strategy_comparison(service: BacktestingService, args):
    """Static Strategy Mix 전략 비교 분석"""
    logger.info("=== Static Strategy Mix 전략 비교 분석 실행 ===")
    
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


def run_macro_analysis(service: BacktestingService, args):
    """거시지표 기반 전략 전용 분석 및 백테스트"""
    logger.info("=== 거시지표 기반 전략 분석 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 현재 거시지표 상태 확인
    try:
        current_macro = get_market_indicator_analysis()
        vix_info = current_macro.get('vix_analysis', {})
        buffett_info = current_macro.get('buffett_analysis', {})
        
        print("\n" + "="*60)
        print("현재 거시지표 상태")
        print("="*60)
        print(f"VIX: {vix_info.get('current_vix', 'N/A')} ({vix_info.get('fear_level', 'UNKNOWN')})")
        print(f"버핏지수: {buffett_info.get('current_value', 'N/A')} ({buffett_info.get('level', 'UNKNOWN')})")
        print(f"시장심리: {current_macro.get('market_sentiment', 'UNKNOWN')}")
        print(f"복합신호: {current_macro.get('combined_signal', 'UNKNOWN')}")
        print("="*60)
    except Exception as e:
        logger.warning(f"거시지표 상태 확인 실패: {e}")
    
    # 거시지표 전략 단독 백테스트
    logger.info("거시지표 전략 백테스트 실행 중...")
    macro_result = service.run_specific_strategy_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        strategy_type=StrategyType.MACRO_DRIVEN,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval
    )
    
    # 기본 전략들과 비교
    logger.info("기존 전략들과 성능 비교 중...")
    comparison_strategies = [
        StrategyType.MACRO_DRIVEN,
        StrategyType.BALANCED,
        StrategyType.CONSERVATIVE,
        StrategyType.MOMENTUM,
        StrategyType.TREND_FOLLOWING
    ]
    
    comparison_result = service.compare_all_strategies(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval,
        strategies=comparison_strategies
    )
    
    # 거시지표 전략 하이라이트 결과 출력
    strategy_results = comparison_result.get('strategy_analysis', {})
    macro_strategy_result = strategy_results.get('macro_driven')
    
    if macro_strategy_result:
        other_results = {k: v for k, v in strategy_results.items() if k != 'macro_driven'}
        avg_return = sum(r['total_return_percent'] for r in other_results.values()) / len(other_results) if other_results else 0
        avg_sharpe = sum(r['sharpe_ratio'] for r in other_results.values()) / len(other_results) if other_results else 0
        
        print(f"\n🎯 거시지표 전략 성과 하이라이트:")
        print(f"  수익률: {macro_strategy_result['total_return_percent']:.2f}% (평균 대비 {macro_strategy_result['total_return_percent'] - avg_return:+.2f}%)")
        print(f"  샤프 비율: {macro_strategy_result['sharpe_ratio']:.2f} (평균 대비 {macro_strategy_result['sharpe_ratio'] - avg_sharpe:+.2f})")
        print(f"  최대 낙폭: {macro_strategy_result['max_drawdown_percent']:.2f}%")
        print(f"  승률: {macro_strategy_result['win_rate']:.1%}")
        
        # 다른 전략 대비 우위 분석
        better_than = len([r for r in other_results.values() if macro_strategy_result['sharpe_ratio'] > r['sharpe_ratio']])
        print(f"  능가한 전략: {better_than}/{len(other_results)}개")
    
    # 전체 비교 결과 출력
    print_strategy_comparison_results(comparison_result)
    
    # 결과 저장
    save_strategy_comparison_results(comparison_result, args)
    
    return comparison_result


def run_dynamic_strategy_backtest(service: BacktestingService, args):
    """동적 전략으로 백테스트 실행"""
    if not args.dynamic_strategy:
        raise ValueError("--dynamic-strategy 인수가 필요합니다.")
    
    logger.info(f"=== {args.dynamic_strategy} 동적 전략 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 동적 전략을 위한 특별한 백테스트 실행
    # 임시로 기존 백테스트를 사용하고, 나중에 동적 전략 엔진 구현
    result = service.run_strategy_backtest(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        data_interval=args.data_interval,
        use_enhanced_signals=True
    )
    
    # 결과 출력
    print_backtest_summary(result, f"{args.dynamic_strategy} 동적 전략 백테스트")
    
    # 상세 리포트 생성 및 저장
    save_backtest_report(service, result, args, f"dynamic_{args.dynamic_strategy}_backtest")
    
    return result


def run_dynamic_strategy_comparison(service: BacktestingService, args):
    """동적 전략들을 비교하는 백테스트 실행"""
    logger.info("=== 동적 전략 비교 백테스트 실행 ===")
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # 비교할 동적 전략들 결정
    dynamic_strategies = args.compare_dynamic_strategies or [
        'dynamic_weight_strategy', 
        'conservative_dynamic_strategy', 
        'aggressive_dynamic_strategy'
    ]
    
    print("\n" + "="*80)
    print("🚀 동적 전략 비교 백테스트")
    print("="*80)
    print(f"테스트 기간: {args.start_date} to {args.end_date}")
    print(f"비교 전략 수: {len(dynamic_strategies)}")
    
    # 각 동적 전략별로 백테스트 실행
    results = {}
    best_strategy = None
    best_sharpe = float('-inf')
    
    for strategy_name in dynamic_strategies:
        logger.info(f"동적 전략 테스트 중: {strategy_name}")
        
        try:
            # 임시로 기존 백테스트를 사용 (나중에 실제 동적 전략 엔진으로 교체)
            result = service.run_strategy_backtest(
                tickers=args.tickers,
                start_date=start_date,
                end_date=end_date,
                initial_capital=args.initial_capital,
                commission_rate=args.commission_rate,
                risk_per_trade=args.risk_per_trade,
                data_interval=args.data_interval,
                use_enhanced_signals=True
            )
            
            results[strategy_name] = result
            
            # 최고 전략 추적
            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_strategy = strategy_name
                
        except Exception as e:
            logger.error(f"동적 전략 {strategy_name} 테스트 실패: {e}")
            continue
    
    # 결과 출력
    print(f"최고 전략 (샤프 비율): {best_strategy or 'None'}")
    print("\n📊 전략별 성과 요약:")
    print("-" * 80)
    print(f"{'전략명':<30} {'수익률':<12} {'샤프비율':<12} {'승률':<8} {'최대낙폭':<12} {'거래수':<8}")
    print("-" * 80)
    
    rankings_sharpe = []
    rankings_return = []
    
    for strategy_name, result in results.items():
        print(f"{strategy_name:<30} "
              f"{result.total_return_percent:>10.2f}% "
              f"{result.sharpe_ratio:>10.2f} "
              f"{result.win_rate:>6.1%} "
              f"{result.max_drawdown_percent:>10.2f}% "
              f"{result.total_trades:>6}")
        
        rankings_sharpe.append((strategy_name, result.sharpe_ratio))
        rankings_return.append((strategy_name, result.total_return_percent))
    
    # 순위 출력
    rankings_sharpe.sort(key=lambda x: x[1], reverse=True)
    rankings_return.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n🏆 순위 (샤프 비율 기준):")
    for i, (name, sharpe) in enumerate(rankings_sharpe, 1):
        print(f"{i}. {name}: {sharpe:.2f}")
    
    print(f"\n💰 순위 (총 수익률 기준):")
    for i, (name, return_pct) in enumerate(rankings_return, 1):
        print(f"{i}. {name}: {return_pct:.2f}%")
    
    print("="*80)
    
    # 결과 저장
    comparison_data = {
        'test_period': f"{args.start_date} to {args.end_date}",
        'strategies_tested': len(dynamic_strategies),
        'best_strategy': best_strategy,
        'results': {name: {
            'total_return_percent': result.total_return_percent,
            'sharpe_ratio': result.sharpe_ratio,
            'win_rate': result.win_rate,
            'max_drawdown_percent': result.max_drawdown_percent,
            'total_trades': result.total_trades
        } for name, result in results.items()},
        'rankings': {
            'by_sharpe': rankings_sharpe,
            'by_return': rankings_return
        }
    }
    
    from pathlib import Path
    import json
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dynamic_strategy_comparison_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n동적 전략 비교 결과가 저장되었습니다: {filepath}")
    
    return results


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
        elif args.mode == 'strategy':
            run_strategy_backtest(service, args)
        elif args.mode == 'strategy-mix':
            run_strategy_mix_backtest(service, args)
        elif args.mode == 'auto-strategy':
            run_auto_strategy_backtest(service, args)
        elif args.mode == 'strategy-comparison':
            run_strategy_comparison(service, args)
        elif args.mode == 'dynamic-strategy':
            run_dynamic_strategy_backtest(service, args)
        elif args.mode == 'dynamic-comparison':
            run_dynamic_strategy_comparison(service, args)
        elif args.mode == 'optimization':
            run_parameter_optimization(service, args)
        elif args.mode == 'walk-forward':
            run_walk_forward_analysis(service, args)
        elif args.mode == 'comparison':
            run_static_mix_strategy_comparison(service, args)
        elif args.mode == 'macro-analysis':
            run_macro_analysis(service, args)
        else:
            raise ValueError(f"지원하지 않는 모드: {args.mode}")
        
        logger.info("백테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 