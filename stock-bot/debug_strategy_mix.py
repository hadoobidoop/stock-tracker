#!/usr/bin/env python3
"""
전략 조합(Strategy Mix) 신호 생성 디버깅 스크립트

balanced_mix, conservative_mix, aggressive_mix가 실제로 신호를 생성하는지
간단한 백테스트를 통해 확인하고 디버깅 정보를 수집합니다.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_strategy_mix_signals():
    """전략 조합 신호 생성 디버깅"""
    
    try:
        print("🔍 전략 조합 신호 생성 디버깅 시작 (실제 데이터)")
        print("=" * 60)
        
        # 1. 필요한 모듈들 import
        from domain.analysis.service.signal_detection_service import SignalDetectionService
        from domain.analysis.config.static_strategies import StrategyType
        from infrastructure.db.models.enums import TrendType
        from domain.analysis.utils.technical_indicators import calculate_all_indicators
        from domain.stock.service.stock_analysis_service import StockAnalysisService
        from domain.stock.repository.stock_repository import StockRepository
        from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
        
        print("✅ 모듈 import 성공")
        
        # 2. 실제 주식 데이터 가져오기
        stock_repository = SQLStockRepository()
        stock_analysis_service = StockAnalysisService(stock_repository)
        test_ticker = "AAPL"
        
        print(f"📊 테스트 종목: {test_ticker}")
        print("📈 실제 주식 데이터 로딩 중...")
        
        # 실제 데이터 가져오기 (최근 3개월)
        try:
            data_dict = stock_repository.fetch_and_cache_ohlcv(
                [test_ticker], 
                90,  # 90일
                "1h"  # 1시간 간격
            )
            
            real_data = data_dict.get(test_ticker)
            if real_data is None or real_data.empty:
                print(f"❌ {test_ticker} 실제 데이터를 가져올 수 없습니다.")
                return
                
            print(f"실제 데이터 로딩 완료: {len(real_data)}개 데이터 포인트")
            print(f"기간: {real_data.index[0]} ~ {real_data.index[-1]}")
            
        except Exception as e:
            print(f"❌ 실제 데이터 로딩 실패: {e}")
            print("📈 샘플 데이터로 대체합니다...")
            # 샘플 데이터 생성 (fallback)
            dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1h')
            np.random.seed(42)
            
            prices = []
            price = 150
            for _ in range(len(dates)):
                change = np.random.normal(0, 0.02) * price
                price = max(price + change, 10)
                prices.append(price)
            
            real_data = pd.DataFrame({
                'Open': prices,
                'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'Close': prices,
                'Volume': [np.random.randint(1000000, 10000000) for _ in range(len(dates))]
            }, index=dates)
        
        # 3. 전략 매니저 직접 테스트
        from domain.analysis.strategy.strategy_manager import StrategyManager
        
        strategy_manager = StrategyManager()
        print("전략 매니저 생성: ✅ 성공")
        
        # 전략 초기화
        success = strategy_manager.initialize_strategies()
        if not success:
            print("❌ 전략 초기화 실패")
            return
        
        print("개별 전략 초기화: ✅ 성공")
        print(f"초기화된 전략 수: {len(strategy_manager.active_strategies)}")
        for strategy_type in strategy_manager.active_strategies:
            print(f"  - {strategy_type.value}")
        
        # 기술적 지표 계산
        try:
            df_with_indicators = calculate_all_indicators(real_data)
            print(f"기술적 지표 계산 완료: {len(df_with_indicators.columns)}개 지표")
            
            # 최신 데이터 일부 출력
            latest = df_with_indicators.iloc[-1]
            print(f"최신 데이터 (Close: ${latest['Close']:.2f}):")
            
            # 주요 지표들 확인
            indicators_to_check = ['rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'sma_5', 'sma_20', 'adx', 'volume', 'stoch_k', 'stoch_d']
            for indicator in indicators_to_check:
                if indicator in df_with_indicators.columns:
                    value = latest.get(indicator, 'N/A')
                    print(f"  {indicator.upper()}: {value:.4f}" if isinstance(value, (int, float)) else f"  {indicator.upper()}: {value}")
                else:
                    print(f"  {indicator.upper()}: ❌ 없음")
            
            # 데이터 품질 확인
            print(f"\n데이터 품질 검증:")
            print(f"  데이터 길이: {len(df_with_indicators)}")
            print(f"  NaN 값 개수: {df_with_indicators.isnull().sum().sum()}")
            print(f"  첫 5개 행의 Close 값: {df_with_indicators['Close'].head().tolist()}")
            print(f"  마지막 5개 행의 Close 값: {df_with_indicators['Close'].tail().tolist()}")
                
        except Exception as e:
            print(f"❌ 기술적 지표 계산 실패: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n" + "=" * 60)
        print("🧪 감지기별 상세 분석 (AGGRESSIVE 전략)")
        print("=" * 60)
        
        # 6. 감지기별 상세 분석
        try:
            # AGGRESSIVE 전략 선택
            strategy_manager.switch_strategy(StrategyType.AGGRESSIVE)
            current_strategy = strategy_manager.current_strategy
            
            if current_strategy and current_strategy.orchestrator:
                print(f"감지기 수: {len(current_strategy.orchestrator.detectors)}")
                
                # 총 점수 계산
                total_buy = 0
                total_sell = 0
                
                # 각 감지기별로 개별 테스트
                for i, detector in enumerate(current_strategy.orchestrator.detectors):
                    print(f"\n🔍 감지기 {i+1}: {detector.name} (가중치: {detector.weight})")
                    
                    try:
                        buy_score, sell_score, buy_details, sell_details = detector.detect_signals(
                            df_with_indicators, TrendType.NEUTRAL, TrendType.NEUTRAL, {}
                        )
                        
                        print(f"  📈 매수 점수: {buy_score:.4f}")
                        print(f"  📉 매도 점수: {sell_score:.4f}")
                        print(f"  📝 매수 근거: {len(buy_details)}개")
                        for detail in buy_details[:2]:  # 최대 2개만
                            print(f"    - {detail}")
                        print(f"  📝 매도 근거: {len(sell_details)}개")
                        for detail in sell_details[:2]:  # 최대 2개만
                            print(f"    - {detail}")
                            
                        # 가중치 적용 후 점수
                        weighted_buy = buy_score * detector.weight
                        weighted_sell = sell_score * detector.weight
                        print(f"  💯 가중치 적용 매수: {weighted_buy:.4f}")
                        print(f"  💯 가중치 적용 매도: {weighted_sell:.4f}")
                        
                        total_buy += weighted_buy
                        total_sell += weighted_sell
                        
                    except Exception as detector_error:
                        print(f"  ❌ 감지기 오류: {detector_error}")
                        import traceback
                        traceback.print_exc()
                
                print(f"\n💯 감지기 총합:")
                print(f"  📈 총 매수 점수: {total_buy:.4f}")
                print(f"  📉 총 매도 점수: {total_sell:.4f}")
                
                # 7. 오케스트레이터 직접 호출 테스트
                print(f"\n🎭 오케스트레이터 직접 호출 테스트:")
                orchestrator_result = current_strategy.orchestrator.detect_signals(
                    df_with_indicators, test_ticker, TrendType.NEUTRAL, TrendType.NEUTRAL, {}
                )
                print(f"  결과 타입: {type(orchestrator_result)}")
                print(f"  결과 내용: {orchestrator_result}")
                print(f"  오케스트레이터 임계값: {current_strategy.orchestrator.signal_threshold}")
                
                # 8. 전략의 analyze 메서드 직접 호출
                print(f"\n🎯 전략 analyze 메서드 직접 호출:")
                strategy_result = current_strategy.analyze(
                    df_with_indicators, test_ticker, TrendType.NEUTRAL, TrendType.NEUTRAL, {}
                )
                print(f"  전략 결과 타입: {type(strategy_result)}")
                print(f"  has_signal: {strategy_result.has_signal}")
                print(f"  total_score: {strategy_result.total_score}")
                print(f"  buy_score: {getattr(strategy_result, 'buy_score', 'N/A')}")
                print(f"  sell_score: {getattr(strategy_result, 'sell_score', 'N/A')}")
                print(f"  전략 임계값: {current_strategy.config.signal_threshold}")
                
            else:
                print("❌ 전략 또는 오케스트레이터를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"❌ 감지기별 분석 실패: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("🧪 개별 전략별 상세 신호 분석")
        print("=" * 60)
        
        # 4. 개별 전략별 상세 분석
        test_strategies = [StrategyType.AGGRESSIVE, StrategyType.BALANCED, StrategyType.MOMENTUM]
        
        for strategy_type in test_strategies:
            print(f"\n🔀 {strategy_type.value} 개별 전략 테스트...")
            
            try:
                # 전략 교체
                success = strategy_manager.switch_strategy(strategy_type)
                if not success:
                    print(f"  ❌ {strategy_type.value} 전략 교체 실패")
                    continue
                
                print(f"  ✅ {strategy_type.value} 전략 교체 성공")
                
                # 신호 감지 시도
                result = strategy_manager.analyze_with_current_strategy(
                    df_with_indicators=df_with_indicators,
                    ticker=test_ticker,
                    market_trend=TrendType.NEUTRAL,
                    long_term_trend=TrendType.NEUTRAL,
                    daily_extra_indicators={}
                )
                
                # 결과 분석
                print(f"  📋 전략명: {result.strategy_name}")
                print(f"  📊 총 점수: {result.total_score:.2f}")
                print(f"  🎯 신호 여부: {'✅ 있음' if result.has_signal else '❌ 없음'}")
                print(f"  💪 신호 강도: {result.signal_strength}")
                print(f"  🎲 신뢰도: {result.confidence:.1%}")
                print(f"  📝 감지된 신호: {len(result.signals_detected)}개")
                for i, signal in enumerate(result.signals_detected[:3], 1):  # 최대 3개까지만
                    print(f"    {i}. {signal}")
                
                # 현재 전략의 임계값 확인
                current_strategy = strategy_manager.current_strategy
                if current_strategy:
                    threshold = current_strategy.config.signal_threshold
                    print(f"  🎚️ 전략 임계값: {threshold}")
                    print(f"  📏 임계값 대비: {(result.total_score / threshold * 100):.1f}%")
                
            except Exception as e:
                print(f"  ❌ {strategy_type.value} 전략 테스트 실패: {e}")
                continue
        
        print("\n" + "=" * 60)
        print("🧪 전략 조합별 신호 생성 테스트")
        print("=" * 60)
        
        # 5. 각 전략 조합 테스트
        test_mixes = ["balanced_mix", "conservative_mix", "aggressive_mix"]
        
        for mix_name in test_mixes:
            print(f"\n🔀 {mix_name} 테스트 중...")
            
            try:
                # 전략 조합 설정
                success = strategy_manager.set_strategy_mix(mix_name)
                if not success:
                    print(f"  ❌ {mix_name} 설정 실패")
                    continue
                
                print(f"  ✅ {mix_name} 설정 성공")
                
                # 신호 감지 시도
                result = strategy_manager.analyze_with_current_strategy(
                    df_with_indicators=df_with_indicators,
                    ticker=test_ticker,
                    market_trend=TrendType.NEUTRAL,
                    long_term_trend=TrendType.NEUTRAL,
                    daily_extra_indicators={}
                )
                
                # 결과 분석
                print(f"  📋 전략명: {result.strategy_name}")
                print(f"  📊 총 점수: {result.total_score:.2f}")
                print(f"  🎯 신호 여부: {'✅ 있음' if result.has_signal else '❌ 없음'}")
                print(f"  💪 신호 강도: {result.signal_strength}")
                print(f"  🎲 신뢰도: {result.confidence:.1%}")
                print(f"  📝 감지된 신호: {len(result.signals_detected)}개")
                for i, signal in enumerate(result.signals_detected[:3], 1):  # 최대 3개까지만
                    print(f"    {i}. {signal}")
                
                # 조합 설정 정보
                mix_config = strategy_manager.current_mix_config
                if mix_config:
                    adjusted_threshold = mix_config.threshold_adjustment * 8.0
                    print(f"  🎚️ 조정된 임계값: {adjusted_threshold}")
                    print(f"  📏 임계값 대비: {(result.total_score / adjusted_threshold * 100):.1f}%")
                    print(f"  🔧 임계값 조정 계수: {mix_config.threshold_adjustment}")
                
            except Exception as e:
                print(f"  ❌ {mix_name} 테스트 실패: {e}")
                continue
        
        print("\n" + "=" * 60)
        print("🏁 전략 조합 신호 생성 디버깅 완료")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 디버깅 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_strategy_mix_signals() 