#!/usr/bin/env python3
"""
전략 조합(Strategy Mix) 설정 테스트 스크립트

새로 생성한 balanced_mix, conservative_mix, aggressive_mix 설정이 
제대로 로드되고 동작하는지 확인하는 테스트 코드
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_strategy_mix_import():
    """전략 조합 설정 import 테스트"""
    print("="*60)
    print("전략 조합 설정 Import 테스트")
    print("="*60)
    
    try:
        from domain.analysis.config.strategy_mixes import (
            StrategyMixMode, StrategyMixConfig, STRATEGY_MIXES,
            MARKET_CONDITION_STRATEGIES, get_strategy_mix_config
        )
        print("✅ strategy_mixes 모듈 import 성공")
        
        # 사용 가능한 전략 조합 확인
        print(f"\n📋 사용 가능한 전략 조합: {len(STRATEGY_MIXES)}개")
        for mix_name, config in STRATEGY_MIXES.items():
            print(f"  • {mix_name}: {config.name}")
            print(f"    - 설명: {config.description}")
            print(f"    - 조합 방식: {config.mode.value}")
            print(f"    - 구성 전략: {list(config.strategies.keys())}")
            print(f"    - 임계값 조정: {config.threshold_adjustment}")
            print()
        
    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


def test_strategy_manager_integration():
    """StrategyManager와의 통합 테스트"""
    print("="*60)
    print("StrategyManager 통합 테스트")
    print("="*60)
    
    try:
        from domain.analysis.strategy.strategy_manager import StrategyManager
        
        print("✅ StrategyManager import 성공")
        
        # StrategyManager 초기화
        manager = StrategyManager()
        print("✅ StrategyManager 초기화 성공")
        
        # 전략 조합 설정 테스트
        test_mixes = ["balanced_mix", "conservative_mix", "aggressive_mix"]
        
        for mix_name in test_mixes:
            print(f"\n🔀 {mix_name} 설정 테스트...")
            success = manager.set_strategy_mix(mix_name)
            if success:
                print(f"✅ {mix_name} 설정 성공")
                
                # 현재 설정된 조합 정보 확인
                if manager.current_mix_config:
                    config = manager.current_mix_config
                    print(f"  - 이름: {config.name}")
                    print(f"  - 조합 방식: {config.mode.value}")
                    print(f"  - 구성 전략 수: {len(config.strategies)}")
            else:
                print(f"❌ {mix_name} 설정 실패")
                return False
        
    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


def test_market_condition_strategies():
    """시장 상황별 권장 전략 테스트"""
    print("="*60)
    print("시장 상황별 권장 전략 테스트")
    print("="*60)
    
    try:
        from domain.analysis.config.strategy_mixes import get_market_condition_strategy
        
        conditions = ["bullish", "bearish", "sideways", "high_volatility", "low_volatility"]
        priorities = ["primary", "secondary", "fallback"]
        
        for condition in conditions:
            print(f"\n📈 {condition} 시장 상황:")
            for priority in priorities:
                strategy = get_market_condition_strategy(condition, priority)
                print(f"  - {priority}: {strategy}")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 전략 조합(Strategy Mix) 설정 테스트 시작\n")
    
    tests = [
        ("Import 테스트", test_strategy_mix_import),
        ("StrategyManager 통합 테스트", test_strategy_manager_integration),
        ("시장 상황별 전략 테스트", test_market_condition_strategies),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name} 실행 중...")
        try:
            if test_func():
                print(f"✅ {test_name} 통과")
                passed += 1
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 실행 중 오류: {e}")
    
    print("\n" + "="*60)
    print(f"테스트 결과: {passed}/{total} 통과")
    print("="*60)
    
    if passed == total:
        print("🎉 모든 테스트 통과! balanced_mix, conservative_mix, aggressive_mix가 정상 동작합니다.")
    else:
        print("⚠️ 일부 테스트 실패. 설정을 다시 확인해주세요.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 