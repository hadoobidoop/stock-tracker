#!/usr/bin/env python3
"""
전략 시스템 데모 스크립트

이 스크립트는 새로운 전략 시스템의 사용법을 보여줍니다:
1. 여러 전략을 미리 로드
2. 동적 전략 교체
3. 전략 조합 사용
4. 모든 전략으로 분석
5. 지표 프리컴퓨팅
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import setup_logging, get_logger
from domain.analysis.service.signal_detection_service import SignalDetectionService
from domain.analysis.config.strategy_settings import StrategyType
from infrastructure.db.models.enums import TrendType

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

def generate_sample_data() -> pd.DataFrame:
    """샘플 OHLCV 데이터 생성"""
    dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='H')
    n = len(dates)
    
    # 간단한 랜덤 워크로 가격 데이터 생성
    import numpy as np
    np.random.seed(42)
    
    close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    highs = close_prices + np.abs(np.random.randn(n) * 0.3)
    lows = close_prices - np.abs(np.random.randn(n) * 0.3)
    opens = close_prices + np.random.randn(n) * 0.2
    volumes = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': close_prices,
        'volume': volumes
    })
    
    df.set_index('timestamp', inplace=True)
    return df

def demo_strategy_switching():
    """전략 교체 데모"""
    print("\n" + "="*60)
    print("🔄 전략 교체 데모")
    print("="*60)
    
    # 서비스 초기화
    service = SignalDetectionService()
    
    # 특정 전략들만 로드 (빠른 데모를 위해)
    strategy_types = [
        StrategyType.CONSERVATIVE,
        StrategyType.BALANCED,
        StrategyType.AGGRESSIVE,
        StrategyType.MOMENTUM
    ]
    
    if not service.initialize(strategy_types):
        print("❌ 서비스 초기화 실패")
        return
    
    print("✅ 서비스 초기화 완료")
    
    # 샘플 데이터 생성 및 지표 계산
    df = generate_sample_data()
    df_with_indicators = service.precompute_indicators_for_ticker("AAPL", df)
    
    print(f"📊 샘플 데이터 생성 완료: {len(df)} 행, {len(df_with_indicators.columns)} 지표")
    
    # 각 전략으로 분석
    ticker = "AAPL"
    market_trend = TrendType.BULLISH
    
    for strategy_type in strategy_types:
        print(f"\n📈 {strategy_type.value} 전략으로 분석 중...")
        
        result = service.detect_signals_with_strategy(
            df_with_indicators, ticker, strategy_type, market_trend
        )
        
        print(f"   전략명: {result.strategy_name}")
        print(f"   총 점수: {result.total_score:.2f}")
        print(f"   신호 존재: {'✅' if result.has_signal else '❌'}")
        print(f"   신호 강도: {result.signal_strength}")
        print(f"   신뢰도: {result.confidence:.2f}")

def demo_strategy_mix():
    """전략 조합 데모"""
    print("\n" + "="*60)
    print("🎯 전략 조합 데모")
    print("="*60)
    
    service = SignalDetectionService()
    
    if not service.initialize():
        print("❌ 서비스 초기화 실패")
        return
    
    # 샘플 데이터
    df = generate_sample_data()
    df_with_indicators = service.precompute_indicators_for_ticker("TSLA", df)
    
    # 미리 정의된 전략 조합 사용
    mix_names = ["balanced_mix", "conservative_mix", "aggressive_mix"]
    
    for mix_name in mix_names:
        print(f"\n🔀 '{mix_name}' 전략 조합 테스트")
        
        if service.set_strategy_mix(mix_name):
            result = service.analyze_with_current_strategy(
                df_with_indicators, "TSLA", TrendType.NEUTRAL
            )
            
            print(f"   조합 전략: {result.strategy_name}")
            print(f"   총 점수: {result.total_score:.2f}")
            print(f"   신뢰도: {result.confidence:.2f}")
            print(f"   신호: {'✅' if result.has_signal else '❌'}")
        else:
            print(f"   ❌ '{mix_name}' 조합 설정 실패")

def demo_all_strategies_analysis():
    """모든 전략 분석 데모"""
    print("\n" + "="*60)
    print("📊 모든 전략 동시 분석 데모")
    print("="*60)
    
    service = SignalDetectionService()
    
    if not service.initialize():
        print("❌ 서비스 초기화 실패")
        return
    
    # 샘플 데이터
    df = generate_sample_data()
    df_with_indicators = service.precompute_indicators_for_ticker("NVDA", df)
    
    print("🚀 모든 전략으로 동시 분석 실행...")
    
    # 모든 전략으로 분석
    results = service.analyze_all_strategies(
        df_with_indicators, "NVDA", TrendType.BULLISH
    )
    
    print(f"\n📈 분석 완료: {len(results)}개 전략 결과")
    print("\n전략별 결과:")
    print("-" * 80)
    print(f"{'전략명':<20} {'점수':<8} {'신호':<6} {'강도':<12} {'신뢰도'}")
    print("-" * 80)
    
    for strategy_type, result in results.items():
        signal_icon = "✅" if result.has_signal else "❌"
        print(f"{result.strategy_name:<20} {result.total_score:<8.2f} {signal_icon:<6} "
              f"{result.signal_strength:<12} {result.confidence:<.2f}")
    
    # 신호 생성한 전략들
    signal_strategies = [r.strategy_name for r in results.values() if r.has_signal]
    if signal_strategies:
        print(f"\n✅ 신호 생성 전략: {', '.join(signal_strategies)}")
    else:
        print("\n❌ 신호를 생성한 전략이 없습니다.")

def demo_indicator_precomputing():
    """지표 프리컴퓨팅 데모"""
    print("\n" + "="*60)
    print("⚡ 지표 프리컴퓨팅 데모")
    print("="*60)
    
    service = SignalDetectionService()
    
    if not service.initialize([StrategyType.BALANCED]):
        print("❌ 서비스 초기화 실패")
        return
    
    # 여러 종목의 데이터 미리 계산
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    print("📊 여러 종목의 지표를 미리 계산 중...")
    
    start_time = datetime.now()
    
    for ticker in tickers:
        print(f"   처리 중: {ticker}")
        
        # 샘플 데이터 생성 (실제로는 DB나 API에서 가져옴)
        df = generate_sample_data()
        
        # 지표 프리컴퓨팅
        df_with_indicators = service.precompute_indicators_for_ticker(ticker, df)
        
        print(f"   완료: {ticker} - {len(df_with_indicators.columns)}개 지표 계산")
    
    computation_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️ 총 계산 시간: {computation_time:.2f}초")
    
    # 캐시 상태 확인
    print(f"💾 캐시된 종목 수: {len(service.precomputed_indicators)}")
    
    # 캐시 히트 테스트
    print("\n🎯 캐시 히트 테스트...")
    start_time = datetime.now()
    
    # 이미 계산된 지표 재요청 (캐시에서 가져와야 함)
    df_cached = service.precompute_indicators_for_ticker("AAPL", df)
    
    cache_time = (datetime.now() - start_time).total_seconds()
    print(f"⚡ 캐시 히트 시간: {cache_time:.4f}초 (매우 빠름!)")

def demo_auto_strategy_selection():
    """자동 전략 선택 데모"""
    print("\n" + "="*60)
    print("🤖 자동 전략 선택 데모")
    print("="*60)
    
    service = SignalDetectionService()
    
    if not service.initialize():
        print("❌ 서비스 초기화 실패")
        return
    
    # 자동 전략 선택 활성화
    service.enable_auto_strategy_selection(True)
    print("✅ 자동 전략 선택 활성화")
    
    # 다양한 시장 상황에서 테스트
    market_conditions = [
        (TrendType.BULLISH, "강세장"),
        (TrendType.BEARISH, "약세장"),
        (TrendType.NEUTRAL, "횡보장")
    ]
    
    df = generate_sample_data()
    df_with_indicators = service.precompute_indicators_for_ticker("SPY", df)
    
    for market_trend, description in market_conditions:
        print(f"\n📈 시장 상황: {description}")
        
        # 현재 전략 확인
        before_strategy = service.get_current_strategy_info()
        print(f"   변경 전 전략: {before_strategy.get('strategy', {}).get('name', '없음')}")
        
        # 분석 실행 (내부적으로 자동 전략 선택 발생)
        result = service.analyze_with_current_strategy(
            df_with_indicators, "SPY", market_trend
        )
        
        # 변경 후 전략 확인
        after_strategy = service.get_current_strategy_info()
        print(f"   변경 후 전략: {after_strategy.get('strategy', {}).get('name', '없음')}")
        print(f"   분석 결과: 점수 {result.total_score:.2f}, 신호 {'있음' if result.has_signal else '없음'}")

def demo_performance_monitoring():
    """성능 모니터링 데모"""
    print("\n" + "="*60)
    print("📊 성능 모니터링 데모")
    print("="*60)
    
    service = SignalDetectionService()
    
    if not service.initialize():
        print("❌ 서비스 초기화 실패")
        return
    
    # 여러 번 분석 실행하여 성능 메트릭 생성
    df = generate_sample_data()
    df_with_indicators = service.precompute_indicators_for_ticker("PERF_TEST", df)
    
    print("🔄 성능 테스트를 위해 여러 번 분석 실행 중...")
    
    for i in range(5):
        service.analyze_with_current_strategy(
            df_with_indicators, "PERF_TEST", TrendType.NEUTRAL
        )
    
    # 성능 요약 확인
    performance = service.get_strategy_performance_summary()
    
    print("\n📊 전략별 성능 요약:")
    print("-" * 60)
    
    for strategy_name, metrics in performance.items():
        print(f"전략: {strategy_name}")
        print(f"  생성된 신호 수: {metrics.get('total_signals_generated', 0)}")
        print(f"  평균 실행 시간: {metrics.get('average_execution_time_ms', 0):.2f}ms")
        print("-" * 40)

def main():
    """메인 데모 실행"""
    print("🚀 Enhanced Signal Detection Service 데모 시작")
    print("="*60)
    
    try:
        # 1. 전략 교체 데모
        demo_strategy_switching()
        
        # 2. 전략 조합 데모
        demo_strategy_mix()
        
        # 3. 모든 전략 분석 데모
        demo_all_strategies_analysis()
        
        # 4. 지표 프리컴퓨팅 데모
        demo_indicator_precomputing()
        
        # 5. 자동 전략 선택 데모
        demo_auto_strategy_selection()
        
        # 6. 성능 모니터링 데모
        demo_performance_monitoring()
        
        print("\n" + "="*60)
        print("✅ 모든 데모가 성공적으로 완료되었습니다!")
        print("="*60)
        
        print("\n💡 사용법 요약:")
        print("1. service = SignalDetectionService()")
        print("2. service.initialize()  # 모든 전략 로드")
        print("3. service.switch_strategy(StrategyType.AGGRESSIVE)  # 전략 교체")
        print("4. service.set_strategy_mix('balanced_mix')  # Static Strategy Mix")
        print("5. service.analyze_all_strategies(df, ticker)  # 모든 전략 분석")
        print("6. service.precompute_indicators_for_ticker(ticker, df)  # 지표 캐시")
        
    except Exception as e:
        logger.error(f"데모 실행 중 오류 발생: {e}")
        print(f"❌ 데모 실행 실패: {e}")

if __name__ == "__main__":
    main() 