#!/usr/bin/env python3
"""
동적 가중치 조절 시스템 데모

이 스크립트는 새로운 동적 전략 시스템이 어떻게 작동하는지 보여줍니다:
1. 거시 경제 상황에 따른 가중치 동적 조절
2. DecisionContext를 통한 상세 로깅
3. Modifier 시스템의 실제 적용
4. 기존 정적 전략 vs 동적 전략 비교

사용법:
    python dynamic_strategy_demo.py
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from domain.analysis.strategy.strategy_manager import StrategyManager
from domain.analysis.strategy.dynamic_strategy import DynamicCompositeStrategy
from domain.analysis.config.dynamic_strategies import get_all_strategies, get_all_modifiers
from domain.analysis.config.static_strategies import StrategyType
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


def create_sample_data() -> pd.DataFrame:
    """
    샘플 가격 데이터 및 기술적 지표 생성
    실제 환경에서는 Yahoo Finance나 다른 데이터 소스에서 가져옵니다.
    """
    print("📊 샘플 데이터 생성 중...")
    
    # 60일간의 가격 데이터 생성
    dates = pd.date_range(start=datetime.now() - timedelta(days=60), periods=60, freq='D')
    
    # 기본 가격 데이터 (무작위 주식 패턴)
    np.random.seed(42)
    price = 100
    prices = []
    volumes = []
    
    for i in range(60):
        # 약간의 변동성을 가진 가격 움직임
        change = np.random.normal(0, 0.02)
        price *= (1 + change)
        prices.append(price)
        
        # 거래량 (가격 변동과 약간 연관)
        volume = int(1000000 * (1 + abs(change) * 5 + np.random.normal(0, 0.1)))
        volumes.append(max(100000, volume))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': volumes
    })
    
    # 기술적 지표 추가 (간단한 버전)
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # RSI 계산
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD 계산
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # 볼륨 관련 지표
    df['volume_sma'] = df['volume'].rolling(window=20).mean()
    
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    df['atr'] = true_range.rolling(window=14).mean()
    
    # Stochastic
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    print(f"✅ {len(df)}일간의 샘플 데이터 생성 완료")
    return df


def create_sample_market_data() -> Dict[str, Any]:
    """
    샘플 거시 지표 데이터 생성
    실제 환경에서는 MarketData 테이블에서 가져옵니다.
    """
    print("🌍 샘플 거시 지표 데이터 생성 중...")
    
    # 다양한 시장 상황을 시뮬레이션
    scenarios = {
        "normal": {
            "VIX": 18.5,
            "FEAR_GREED_INDEX": 55,
            "DXY": 103.2,
            "US_10Y_TREASURY_YIELD": 4.2,
            "SP500_INDEX": 4200,
            "BUFFETT_INDICATOR": 185,
            "PUT_CALL_RATIO": 0.8
        },
        "high_volatility": {
            "VIX": 32.1,
            "FEAR_GREED_INDEX": 25,
            "DXY": 106.8,
            "US_10Y_TREASURY_YIELD": 4.8,
            "SP500_INDEX": 4050,
            "BUFFETT_INDICATOR": 190,
            "PUT_CALL_RATIO": 1.2
        },
        "extreme_fear": {
            "VIX": 38.5,
            "FEAR_GREED_INDEX": 15,
            "DXY": 108.2,
            "US_10Y_TREASURY_YIELD": 5.1,
            "SP500_INDEX": 3900,
            "BUFFETT_INDICATOR": 195,
            "PUT_CALL_RATIO": 1.5
        },
        "bull_market": {
            "VIX": 12.3,
            "FEAR_GREED_INDEX": 85,
            "DXY": 101.5,
            "US_10Y_TREASURY_YIELD": 3.8,
            "SP500_INDEX": 4500,
            "BUFFETT_INDICATOR": 180,
            "PUT_CALL_RATIO": 0.6
        }
    }
    
    return scenarios


def demonstrate_dynamic_strategy():
    """동적 전략 시스템 데모"""
    print("=" * 60)
    print("🚀 동적 가중치 조절 시스템 데모")
    print("=" * 60)
    
    # 1. 전략 매니저 초기화
    print("\n1️⃣ StrategyManager 초기화...")
    manager = StrategyManager()
    
    # 기존 정적 전략들 초기화
    success = manager.initialize_strategies([StrategyType.BALANCED, StrategyType.CONSERVATIVE])
    if not success:
        print("❌ 전략 초기화 실패")
        return
    
    print(f"✅ 전략 초기화 성공: {len(manager.active_strategies)} 정적 전략, {len(manager.dynamic_strategies)} 동적 전략")
    
    # 2. 사용 가능한 전략 목록 확인
    print("\n2️⃣ 사용 가능한 전략 목록:")
    strategies = manager.get_available_strategies()
    for strategy in strategies:
        status = "🟢 현재 활성" if strategy['is_current'] else "⚪ 대기 중"
        print(f"  {status} {strategy['name']} ({strategy['strategy_class']})")
        if strategy['strategy_class'] == 'dynamic':
            print(f"      📋 {strategy['description']}")
    
    # 3. 샘플 데이터 생성
    df = create_sample_data()
    market_scenarios = create_sample_market_data()
    
    # 4. 다양한 시장 상황에서 분석 비교
    print("\n3️⃣ 다양한 시장 상황에서 전략 분석 비교")
    
    test_ticker = "AAPL"
    
    for scenario_name, market_data in market_scenarios.items():
        print(f"\n📈 시나리오: {scenario_name.upper()}")
        print(f"   VIX: {market_data['VIX']}, Fear&Greed: {market_data['FEAR_GREED_INDEX']}")
        
        # 정적 전략 분석 (Balanced)
        manager.switch_strategy(StrategyType.BALANCED)
        static_result = manager.analyze_with_current_strategy(
            df, test_ticker, TrendType.NEUTRAL, TrendType.NEUTRAL, market_data
        )
        
        # 동적 전략 분석
        manager.switch_to_dynamic_strategy("dynamic_weight_strategy")
        dynamic_result = manager.analyze_with_current_strategy(
            df, test_ticker, TrendType.NEUTRAL, TrendType.NEUTRAL, market_data
        )
        
        # 결과 비교
        print(f"   🔵 정적 전략 (Balanced): 점수 {static_result.total_score:.2f}, 신호 {'✅' if static_result.has_signal else '❌'}")
        print(f"   🟡 동적 전략: 점수 {dynamic_result.total_score:.2f}, 신호 {'✅' if dynamic_result.has_signal else '❌'}")
        
        # 동적 전략의 상세 정보 출력
        if hasattr(manager, 'current_dynamic_strategy') and manager.current_dynamic_strategy:
            context = manager.current_dynamic_strategy.get_last_decision_context()
            if context:
                print(f"      📊 가중치 조정: {len(context.weight_adjustments)}개")
                print(f"      🔧 모디파이어 적용: {len([m for m in context.modifier_applications if m.applied])}개")
                if context.is_vetoed:
                    print(f"      🚫 거부됨: {context.veto_reason}")


def demonstrate_decision_context_details():
    """DecisionContext의 상세 로깅 기능 데모"""
    print("\n4️⃣ DecisionContext 상세 로깅 데모")
    
    manager = StrategyManager()
    manager.initialize_strategies()
    manager.switch_to_dynamic_strategy("dynamic_weight_strategy")
    
    # 고변동성 시나리오로 분석
    df = create_sample_data()
    market_data = {
        "VIX": 35.0,  # 극도의 공포
        "FEAR_GREED_INDEX": 15,
        "DXY": 108.0,
        "US_10Y_TREASURY_YIELD": 5.0,
        "SP500_INDEX": 3900
    }
    
    result = manager.analyze_with_current_strategy(
        df, "DEMO", TrendType.NEUTRAL, TrendType.NEUTRAL, market_data
    )
    
    # 상세 로그 출력
    if manager.current_dynamic_strategy:
        logs = manager.get_dynamic_strategy_detailed_log()
        print(f"\n📜 상세 분석 로그 ({len(logs)}개 단계):")
        
        for i, log in enumerate(logs):
            timestamp = log['timestamp'][:19]  # 초까지만 표시
            print(f"  {i+1:2d}. [{timestamp}] {log['step']}: {log['action']}")
            if log['details']:
                for key, value in log['details'].items():
                    if isinstance(value, dict):
                        print(f"      {key}: {len(value)} items")
                    else:
                        print(f"      {key}: {value}")
        
        # 컨텍스트 요약
        summary = manager.get_dynamic_strategy_info()
        if 'last_analysis' in summary:
            analysis = summary['last_analysis']
            print(f"\n📋 분석 요약:")
            print(f"   최종 점수: {analysis['final_score']:.2f}")
            print(f"   임계값: {analysis['final_threshold']:.2f}")
            print(f"   신호 타입: {analysis['signal_type']}")
            print(f"   신뢰도: {analysis['confidence']:.1%}")
            print(f"   모디파이어 적용: {analysis['modifiers_applied']}/{analysis['total_modifiers_evaluated']}")


def demonstrate_modifier_system():
    """Modifier 시스템의 동작 데모"""
    print("\n5️⃣ Modifier 시스템 동작 데모")
    
    # 모든 모디파이어 정의 출력
    modifiers = get_all_modifiers()
    print(f"\n📋 정의된 모디파이어: {len(modifiers)}개")
    
    for name, definition in list(modifiers.items())[:5]:  # 처음 5개만 출력
        print(f"   🔧 {name}")
        print(f"      📝 {definition.description}")
        print(f"      ⚡ 액션: {definition.action.type.value}")
        print(f"      🎯 우선순위: {definition.priority}")
    
    # 각기 다른 시장 상황에서 어떤 모디파이어가 활성화되는지 보여주기
    scenarios = {
        "극도 공포": {"VIX": 40, "FEAR_GREED_INDEX": 10},
        "일반 상황": {"VIX": 18, "FEAR_GREED_INDEX": 55}, 
        "극도 탐욕": {"VIX": 12, "FEAR_GREED_INDEX": 90},
        "고금리": {"VIX": 20, "US_10Y_TREASURY_YIELD": 5.5},
        "달러 강세": {"VIX": 22, "DXY": 110}
    }
    
    manager = StrategyManager()
    manager.initialize_strategies()
    manager.switch_to_dynamic_strategy("dynamic_weight_strategy")
    
    df = create_sample_data()
    
    print("\n🎭 시나리오별 모디파이어 활성화:")
    for scenario_name, market_data in scenarios.items():
        print(f"\n   📊 {scenario_name}:")
        for key, value in market_data.items():
            print(f"      {key}: {value}")
        
        result = manager.analyze_with_current_strategy(
            df, "TEST", TrendType.NEUTRAL, TrendType.NEUTRAL, market_data
        )
        
        if manager.current_dynamic_strategy:
            context = manager.current_dynamic_strategy.get_last_decision_context()
            if context:
                applied_modifiers = [m for m in context.modifier_applications if m.applied]
                print(f"      ✅ 활성화된 모디파이어: {len(applied_modifiers)}개")
                for modifier in applied_modifiers:
                    print(f"         🔧 {modifier.modifier_name}: {modifier.reason}")


def main():
    """메인 함수"""
    try:
        print("🎯 동적 가중치 조절 시스템 데모를 시작합니다!")
        print("이 데모는 거시 경제 상황에 따른 지능형 가중치 조절을 보여줍니다.\n")
        
        # 1. 기본 동적 전략 데모
        demonstrate_dynamic_strategy()
        
        # 2. DecisionContext 상세 로깅 데모  
        demonstrate_decision_context_details()
        
        # 3. Modifier 시스템 데모
        demonstrate_modifier_system()
        
        print("\n" + "=" * 60)
        print("🎉 데모 완료!")
        print("=" * 60)
        print("\n💡 주요 특징:")
        print("  ✅ 거시 지표에 따른 실시간 가중치 조절")
        print("  ✅ 투명한 의사결정 과정 추적")
        print("  ✅ 모듈화된 Modifier 시스템")
        print("  ✅ 기존 정적 전략과의 완벽한 호환성")
        print("\n🚀 이제 실제 거래 환경에서 사용할 준비가 되었습니다!")
        
    except Exception as e:
        logger.error(f"데모 실행 중 오류 발생: {e}")
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 