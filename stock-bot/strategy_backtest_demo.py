#!/usr/bin/env python3
"""
전략 백테스팅 데모

새로운 다중 전략 시스템을 활용한 백테스팅 기능들을 시연합니다.

시연 내용:
1. 특정 전략 백테스팅 (AGGRESSIVE vs CONSERVATIVE)
2. 전략 조합 백테스팅 (balanced_mix)
3. 자동 전략 선택 백테스팅
4. 전략 비교 백테스팅 (모든 전략 비교)
5. 레거시 시스템과 성능 비교
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import get_logger
from domain.backtesting.service.backtesting_service import BacktestingService
from domain.analysis.config.strategy_settings import StrategyType

logger = get_logger(__name__)


def demo_specific_strategy_backtest():
    """특정 전략 백테스팅 데모"""
    print("\n" + "="*80)
    print("🎯 특정 전략 백테스팅 데모")
    print("="*80)
    
    service = BacktestingService()
    
    # 테스트 설정
    tickers = ['AAPL', 'MSFT']  # 간단한 테스트를 위해 2개 종목만
    start_date = datetime.now() - timedelta(days=90)  # 3개월
    end_date = datetime.now() - timedelta(days=1)
    
    print(f"테스트 종목: {tickers}")
    print(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # AGGRESSIVE 전략 테스트
    print("\n🔥 AGGRESSIVE 전략 백테스팅...")
    try:
        aggressive_result = service.run_specific_strategy_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            strategy_type=StrategyType.AGGRESSIVE,
            initial_capital=50000.0  # 작은 금액으로 테스트
        )
        
        print(f"AGGRESSIVE 전략 결과:")
        print(f"  총 수익률: {aggressive_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {aggressive_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {aggressive_result.total_trades}")
        print(f"  승률: {aggressive_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"AGGRESSIVE 전략 오류: {e}")
    
    # CONSERVATIVE 전략 테스트
    print("\n🛡️ CONSERVATIVE 전략 백테스팅...")
    try:
        conservative_result = service.run_specific_strategy_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            strategy_type=StrategyType.CONSERVATIVE,
            initial_capital=50000.0
        )
        
        print(f"CONSERVATIVE 전략 결과:")
        print(f"  총 수익률: {conservative_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {conservative_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {conservative_result.total_trades}")
        print(f"  승률: {conservative_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"CONSERVATIVE 전략 오류: {e}")


def demo_strategy_mix_backtest():
    """전략 조합 백테스팅 데모"""
    print("\n" + "="*80)
    print("🎭 전략 조합 백테스팅 데모")
    print("="*80)
    
    service = BacktestingService()
    
    # 테스트 설정
    tickers = ['AAPL']  # 단일 종목으로 빠른 테스트
    start_date = datetime.now() - timedelta(days=60)  # 2개월
    end_date = datetime.now() - timedelta(days=1)
    
    print(f"테스트 종목: {tickers}")
    print(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # balanced_mix 전략 조합 테스트
    print("\n⚖️ balanced_mix 전략 조합 백테스팅...")
    try:
        mix_result = service.run_strategy_mix_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            mix_name='balanced_mix',
            initial_capital=30000.0
        )
        
        print(f"balanced_mix 전략 조합 결과:")
        print(f"  총 수익률: {mix_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {mix_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {mix_result.total_trades}")
        print(f"  승률: {mix_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"전략 조합 오류: {e}")


def demo_auto_strategy_backtest():
    """자동 전략 선택 백테스팅 데모"""
    print("\n" + "="*80)
    print("🤖 자동 전략 선택 백테스팅 데모")
    print("="*80)
    
    service = BacktestingService()
    
    # 테스트 설정
    tickers = ['MSFT']  # 단일 종목으로 빠른 테스트
    start_date = datetime.now() - timedelta(days=45)  # 1.5개월
    end_date = datetime.now() - timedelta(days=1)
    
    print(f"테스트 종목: {tickers}")
    print(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    print("\n🤖 자동 전략 선택 백테스팅...")
    try:
        auto_result = service.run_auto_strategy_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=30000.0
        )
        
        print(f"자동 전략 선택 결과:")
        print(f"  총 수익률: {auto_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {auto_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {auto_result.total_trades}")
        print(f"  승률: {auto_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"자동 전략 선택 오류: {e}")


def demo_strategy_comparison():
    """전략 비교 백테스팅 데모"""
    print("\n" + "="*80)
    print("📊 전략 비교 백테스팅 데모")
    print("="*80)
    
    service = BacktestingService()
    
    # 테스트 설정
    tickers = ['AAPL']  # 단일 종목으로 빠른 테스트
    start_date = datetime.now() - timedelta(days=30)  # 1개월
    end_date = datetime.now() - timedelta(days=1)
    
    # 비교할 전략들 (일부만 선택하여 빠른 테스트)
    strategies = [
        StrategyType.CONSERVATIVE,
        StrategyType.BALANCED,
        StrategyType.AGGRESSIVE
    ]
    
    print(f"테스트 종목: {tickers}")
    print(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"비교 전략: {[s.value for s in strategies]}")
    
    print("\n📊 전략 비교 분석 중...")
    try:
        comparison_result = service.compare_all_strategies(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=30000.0,
            strategies=strategies
        )
        
        # 결과 요약 출력
        summary = comparison_result['comparison_summary']
        analysis = comparison_result['strategy_analysis']
        
        print(f"\n📈 전략 비교 결과:")
        print(f"최고 전략: {summary['best_strategy']}")
        
        print(f"\n전략별 성과:")
        for strategy_name, data in analysis.items():
            print(f"  {strategy_name}:")
            print(f"    수익률: {data['total_return_percent']:>6.2f}%")
            print(f"    샤프비율: {data['sharpe_ratio']:>6.2f}")
            print(f"    승률: {data['win_rate']:>8.1%}")
            print(f"    거래수: {data['total_trades']:>6}")
        
    except Exception as e:
        print(f"전략 비교 오류: {e}")


def demo_legacy_vs_enhanced():
    """레거시 시스템 vs 향상된 시스템 비교"""
    print("\n" + "="*80)
    print("🔄 레거시 vs 향상된 시스템 비교")
    print("="*80)
    
    service = BacktestingService()
    
    # 테스트 설정
    tickers = ['AAPL']
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now() - timedelta(days=1)
    
    print(f"테스트 종목: {tickers}")
    print(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 레거시 시스템 테스트
    print("\n🕰️ 레거시 시스템 백테스팅...")
    try:
        legacy_result = service.run_strategy_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=30000.0,
            use_enhanced_signals=False  # 레거시 시스템 사용
        )
        
        print(f"레거시 시스템 결과:")
        print(f"  총 수익률: {legacy_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {legacy_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {legacy_result.total_trades}")
        print(f"  승률: {legacy_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"레거시 시스템 오류: {e}")
    
    # 향상된 시스템 테스트 (BALANCED 전략)
    print("\n🚀 향상된 시스템 백테스팅 (BALANCED 전략)...")
    try:
        enhanced_result = service.run_strategy_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=30000.0,
            strategy_type=StrategyType.BALANCED,
            use_enhanced_signals=True  # 새로운 시스템 사용
        )
        
        print(f"향상된 시스템 결과:")
        print(f"  총 수익률: {enhanced_result.total_return_percent:.2f}%")
        print(f"  샤프 비율: {enhanced_result.sharpe_ratio:.2f}")
        print(f"  총 거래: {enhanced_result.total_trades}")
        print(f"  승률: {enhanced_result.win_rate:.1%}")
        
    except Exception as e:
        print(f"향상된 시스템 오류: {e}")


def main():
    """메인 데모 함수"""
    print("🎯 전략 백테스팅 시스템 데모")
    print("=" * 80)
    print("새로운 다중 전략 시스템을 활용한 백테스팅 기능들을 시연합니다.")
    print("주의: 데모용이므로 짧은 기간과 적은 종목으로 테스트합니다.")
    
    try:
        # 1. 특정 전략 백테스팅
        demo_specific_strategy_backtest()
        
        # 2. 전략 조합 백테스팅
        demo_strategy_mix_backtest()
        
        # 3. 자동 전략 선택 백테스팅
        demo_auto_strategy_backtest()
        
        # 4. 전략 비교 백테스팅
        demo_strategy_comparison()
        
        # 5. 레거시 vs 향상된 시스템 비교
        demo_legacy_vs_enhanced()
        
        print("\n" + "="*80)
        print("✅ 전략 백테스팅 데모 완료!")
        print("="*80)
        print("실제 사용시에는 더 긴 기간과 더 많은 종목으로 테스트하시기 바랍니다.")
        print("명령행 도구: python run_backtest.py --help")
        
    except Exception as e:
        logger.error(f"데모 실행 중 오류: {e}", exc_info=True)
        print(f"\n❌ 데모 실행 중 오류가 발생했습니다: {e}")
        print("이는 데이터 부족 또는 설정 문제일 수 있습니다.")


if __name__ == '__main__':
    main() 