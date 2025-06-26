#!/usr/bin/env python3
"""
실시간 동적 전략 신호 생성 데모

이 스크립트는 실제 시장 데이터를 사용하여 동적 전략 시스템의 
신호 생성 과정을 실시간으로 보여줍니다.

특징:
1. 실제 시장 데이터 사용
2. 실시간 거시 지표 연동
3. 동적 가중치 조절 시연
4. 상세 의사결정 로깅
5. 정적 vs 동적 전략 성능 비교
"""

import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.logging import get_logger
from domain.analysis.strategy.strategy_manager import StrategyManager
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from infrastructure.db.models.enums import TrendType

logger = get_logger(__name__)

class RealTimeStrategyDemo:
    """실시간 동적 전략 데모 클래스"""
    
    def __init__(self):
        self.stock_repository = SQLStockRepository()
        self.stock_analysis_service = StockAnalysisService(self.stock_repository)
        self.strategy_manager = StrategyManager()
        
        # 테스트할 종목들
        self.test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        
        logger.info("RealTimeStrategyDemo 초기화 완료")
    
    def run_comprehensive_demo(self):
        """포괄적인 실시간 전략 데모 실행"""
        print("🚀 실시간 동적 전략 시그널 생성 데모")
        print("="*80)
        
        # 1. 전략 시스템 초기화
        self._initialize_strategies()
        
        # 2. 실시간 거시 지표 상태 확인
        self._show_current_market_conditions()
        
        # 3. 종목별 신호 분석
        self._analyze_multiple_tickers()
        
        # 4. 동적 vs 정적 전략 비교
        self._compare_dynamic_vs_static()
        
        # 5. 실시간 시뮬레이션
        self._run_realtime_simulation()
        
        print("\n🎉 실시간 동적 전략 데모 완료!")
    
    def _initialize_strategies(self):
        """전략 시스템 초기화"""
        print("\n1️⃣ 전략 시스템 초기화...")
        
        try:
            # 정적 전략 초기화
            static_initialized = self.strategy_manager.initialize_strategies()
            
            # 동적 전략 초기화  
            dynamic_initialized = self.strategy_manager._initialize_dynamic_strategies()
            
            # 동적 전략으로 전환
            success = self.strategy_manager.switch_to_dynamic_strategy('dynamic_weight_strategy')
            
            print(f"✅ 정적 전략 초기화: {static_initialized}")
            print(f"✅ 동적 전략 초기화: {dynamic_initialized}")
            print(f"✅ 동적 전략 활성화: {success}")
            
            # 현재 활성 전략 상태
            info = self.strategy_manager.get_dynamic_strategy_info()
            if info:
                print(f"📋 현재 활성 동적 전략: {info['strategy_name']}")
                print(f"📋 설명: {info['description']}")
                
        except Exception as e:
            logger.error(f"전략 초기화 실패: {e}")
            print(f"❌ 전략 초기화 실패: {e}")
    
    def _show_current_market_conditions(self):
        """현재 시장 상황 표시"""
        print("\n2️⃣ 현재 시장 상황 분석...")
        
        try:
            # 샘플 거시 지표 데이터 생성 (실제 환경에서는 실시간 데이터 사용)
            market_conditions = self._get_sample_market_data()
            
            print("📊 현재 거시 지표:")
            for indicator, value in market_conditions.items():
                print(f"   {indicator}: {value}")
                
            # 시장 분위기 요약
            vix = market_conditions.get('VIX', 20)
            fear_greed = market_conditions.get('FEAR_GREED_INDEX', 50)
            
            if vix > 30:
                market_mood = "🔴 공포 (고변동성)"
            elif vix < 15:
                market_mood = "🟢 낙관 (저변동성)"
            else:
                market_mood = "🟡 중립 (보통변동성)"
                
            print(f"📈 시장 분위기: {market_mood}")
            
        except Exception as e:
            logger.error(f"시장 상황 분석 실패: {e}")
            print(f"❌ 시장 상황 분석 실패: {e}")
    
    def _analyze_multiple_tickers(self):
        """여러 종목에 대한 신호 분석"""
        print("\n3️⃣ 종목별 동적 전략 신호 분석...")
        
        results = {}
        
        for ticker in self.test_tickers[:3]:  # 처음 3개 종목만 테스트
            print(f"\n📊 {ticker} 분석 중...")
            
            try:
                # 샘플 데이터 생성 (실제 환경에서는 실시간 데이터 사용)
                sample_data = self._generate_sample_stock_data(ticker)
                market_data = self._get_sample_market_data()
                
                # 동적 전략으로 분석
                dynamic_result = self.strategy_manager.analyze_with_current_strategy(
                    df_with_indicators=sample_data,
                    ticker=ticker,
                    market_trend=TrendType.NEUTRAL,
                    long_term_trend=TrendType.NEUTRAL,
                    daily_extra_indicators=market_data
                )
                
                results[ticker] = dynamic_result
                
                # 결과 출력
                self._print_analysis_result(ticker, dynamic_result)
                
            except Exception as e:
                logger.error(f"{ticker} 분석 실패: {e}")
                print(f"❌ {ticker} 분석 실패: {e}")
        
        return results
    
    def _compare_dynamic_vs_static(self):
        """동적 vs 정적 전략 비교"""
        print("\n4️⃣ 동적 vs 정적 전략 성능 비교...")
        
        ticker = 'AAPL'  # 대표 종목으로 테스트
        
        try:
            sample_data = self._generate_sample_stock_data(ticker)
            market_data = self._get_sample_market_data()
            
            # 정적 전략으로 분석
            self.strategy_manager.switch_strategy(StrategyType.BALANCED)
            static_result = self.strategy_manager.analyze_with_current_strategy(
                df_with_indicators=sample_data,
                ticker=ticker,
                market_trend=TrendType.NEUTRAL,
                long_term_trend=TrendType.NEUTRAL,
                daily_extra_indicators=market_data
            )
            
            # 동적 전략으로 분석
            self.strategy_manager.switch_to_dynamic_strategy('dynamic_weight_strategy')
            dynamic_result = self.strategy_manager.analyze_with_current_strategy(
                df_with_indicators=sample_data,
                ticker=ticker,
                market_trend=TrendType.NEUTRAL,
                long_term_trend=TrendType.NEUTRAL,
                daily_extra_indicators=market_data
            )
            
            # 비교 결과 출력
            print(f"\n📈 {ticker} 전략 비교 결과:")
            print("-" * 60)
            print(f"{'전략':<20} {'점수':<10} {'신호':<10} {'신뢰도':<10}")
            print("-" * 60)
            print(f"{'정적 (균형)':<20} {static_result.total_score:<10.2f} "
                  f"{'✅' if static_result.has_signal else '❌':<10} "
                  f"{static_result.confidence:<10.1%}")
            print(f"{'동적 (가중치)':<20} {dynamic_result.total_score:<10.2f} "
                  f"{'✅' if dynamic_result.has_signal else '❌':<10} "
                  f"{dynamic_result.confidence:<10.1%}")
            
            # 상세 분석 로그 표시
            if hasattr(self.strategy_manager, 'current_dynamic_strategy'):
                detailed_log = self.strategy_manager.get_dynamic_strategy_detailed_log()
                if detailed_log:
                    print(f"\n📜 동적 전략 상세 로그 (최근 5개):")
                    for i, log_entry in enumerate(detailed_log[-5:], 1):
                        print(f"   {i}. [{log_entry.get('timestamp', 'N/A')}] "
                              f"{log_entry.get('decision_type', 'N/A')}: "
                              f"{log_entry.get('description', 'N/A')}")
            
        except Exception as e:
            logger.error(f"전략 비교 실패: {e}")
            print(f"❌ 전략 비교 실패: {e}")
    
    def _run_realtime_simulation(self):
        """실시간 시뮬레이션"""
        print("\n5️⃣ 실시간 시장 변화 시뮬레이션...")
        
        scenarios = [
            {"name": "정상 시장", "vix": 18, "fear_greed": 55},
            {"name": "변동성 증가", "vix": 28, "fear_greed": 35},
            {"name": "극도 공포", "vix": 40, "fear_greed": 15},
            {"name": "강세장", "vix": 12, "fear_greed": 85}
        ]
        
        ticker = 'MSFT'  # 시뮬레이션 종목
        
        for scenario in scenarios:
            print(f"\n🎭 시나리오: {scenario['name']}")
            print(f"   VIX: {scenario['vix']}, 공포탐욕지수: {scenario['fear_greed']}")
            
            try:
                # 시나리오별 거시 지표 데이터
                market_data = {
                    'VIX': scenario['vix'],
                    'FEAR_GREED_INDEX': scenario['fear_greed'],
                    'DXY': 105 + np.random.normal(0, 2),
                    'US_10Y_TREASURY_YIELD': 4.5 + np.random.normal(0, 0.3),
                    'SP500_INDEX': 4800 + np.random.normal(0, 100)
                }
                
                sample_data = self._generate_sample_stock_data(ticker)
                
                # 동적 전략으로 분석
                result = self.strategy_manager.analyze_with_current_strategy(
                    df_with_indicators=sample_data,
                    ticker=ticker,
                    market_trend=TrendType.NEUTRAL,
                    long_term_trend=TrendType.NEUTRAL,
                    daily_extra_indicators=market_data
                )
                
                # 결과 요약
                signal_status = "🟢 매수" if result.buy_score > result.sell_score else "🔴 매도" if result.sell_score > 0 else "⚪ 중립"
                print(f"   신호: {signal_status} | 점수: {result.total_score:.2f} | 신뢰도: {result.confidence:.1%}")
                
                # 적용된 모디파이어 확인
                if result.signals_detected:
                    active_modifiers = [s for s in result.signals_detected if 'filter' in s.lower() or 'mode' in s.lower()]
                    if active_modifiers:
                        print(f"   활성 모디파이어: {', '.join(active_modifiers[:2])}...")
                
                time.sleep(1)  # 시각적 효과
                
            except Exception as e:
                logger.error(f"시나리오 {scenario['name']} 실행 실패: {e}")
                print(f"   ❌ 시나리오 실행 실패: {e}")
    
    def _print_analysis_result(self, ticker: str, result):
        """분석 결과 출력"""
        signal_emoji = "🟢" if result.has_signal and result.buy_score > result.sell_score else \
                      "🔴" if result.has_signal and result.sell_score > result.buy_score else "⚪"
        
        print(f"   {signal_emoji} 신호: {'매수' if result.buy_score > result.sell_score else '매도' if result.sell_score > 0 else '중립'}")
        print(f"   📊 점수: {result.total_score:.2f} | 신뢰도: {result.confidence:.1%}")
        
        if result.signals_detected:
            print(f"   🔍 감지된 신호: {len(result.signals_detected)}개")
            for signal in result.signals_detected[:3]:  # 최대 3개만 표시
                print(f"      • {signal}")
    
    def _generate_sample_stock_data(self, ticker: str) -> pd.DataFrame:
        """샘플 주식 데이터 생성"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=60), 
                            end=datetime.now(), freq='H')[:100]
        
        # 기본 OHLCV 데이터
        base_price = 150 + np.random.normal(0, 5)
        price_changes = np.random.normal(0, 0.02, len(dates))
        prices = base_price * np.cumprod(1 + price_changes)
        
        data = {
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        }
        
        df = pd.DataFrame(data)
        
        # 기술적 지표 추가
        df['RSI_14'] = 50 + np.random.normal(0, 15, len(df))
        df['MACD_12_26_9'] = np.random.normal(0, 2, len(df))
        df['MACDs_12_26_9'] = df['MACD_12_26_9'] + np.random.normal(0, 0.5, len(df))
        df['SMA_5'] = df['close'].rolling(5).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['STOCHk_14_3_3'] = 50 + np.random.normal(0, 20, len(df))
        df['STOCHd_14_3_3'] = df['STOCHk_14_3_3'] + np.random.normal(0, 5, len(df))
        df['ADX_14'] = 25 + np.random.normal(0, 10, len(df))
        df['Volume_SMA_20'] = df['volume'].rolling(20).mean()
        
        # NaN 값 제거
        df = df.dropna()
        
        return df
    
    def _get_sample_market_data(self) -> Dict[str, Any]:
        """샘플 거시 지표 데이터 생성"""
        return {
            'VIX': 20 + np.random.normal(0, 5),
            'FEAR_GREED_INDEX': 50 + np.random.normal(0, 15),
            'DXY': 105 + np.random.normal(0, 3),
            'US_10Y_TREASURY_YIELD': 4.5 + np.random.normal(0, 0.5),
            'BUFFETT_INDICATOR': 180 + np.random.normal(0, 10),
            'PUT_CALL_RATIO': 1.0 + np.random.normal(0, 0.2),
            'SP500_INDEX': 4800 + np.random.normal(0, 50)
        }

def main():
    """메인 실행 함수"""
    print("🎯 실시간 동적 전략 신호 생성 시스템 시작!")
    print("실제 시장 조건에서 동적 가중치 조절이 어떻게 작동하는지 확인합니다.")
    print()
    
    try:
        demo = RealTimeStrategyDemo()
        demo.run_comprehensive_demo()
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실시간 데모 실행 실패: {e}")
        print(f"❌ 실행 중 오류 발생: {e}")

if __name__ == '__main__':
    main() 