#!/usr/bin/env python3
"""
VIX 분석 테스트 스크립트
"""
import sys
import os
sys.path.append(os.getcwd())

from infrastructure.logging import setup_logging
from domain.analysis.utils.market_indicators import MarketIndicatorAnalyzer

def test_vix_analysis():
    """VIX 분석 테스트"""
    setup_logging()
    
    print("=== VIX 분석 테스트 시작 ===")
    
    try:
        analyzer = MarketIndicatorAnalyzer()
        
        # VIX 분석
        print("1. VIX 단독 분석...")
        vix_analysis = analyzer.get_vix_analysis()
        
        if vix_analysis:
            print(f"현재 VIX: {vix_analysis.get('current_vix', 'N/A')}")
            print(f"VIX 평균: {vix_analysis.get('vix_mean', 'N/A'):.2f}")
            print(f"VIX 변화율: {vix_analysis.get('vix_change_pct', 'N/A'):+.2f}%")
            print(f"공포 레벨: {vix_analysis.get('fear_level', 'N/A')}")
            print(f"VIX 트렌드: {vix_analysis.get('trend', 'N/A')}")
            
            trading_signal = vix_analysis.get('trading_signal', {})
            if trading_signal.get('type'):
                print(f"거래 신호: {trading_signal['type']} (강도: {trading_signal.get('strength', 0):.1f}, 신뢰도: {trading_signal.get('confidence', 0):.2f})")
                print(f"신호 근거: {', '.join(trading_signal.get('reason', []))}")
            else:
                print("거래 신호: 없음")
        else:
            print("VIX 분석 실패")
        
        # 버핏 지수 분석
        print("\n2. 버핏 지수 분석...")
        buffett_analysis = analyzer.get_buffett_indicator_analysis()
        
        if buffett_analysis:
            print(f"현재 버핏 지수: {buffett_analysis.get('current_value', 'N/A'):.1f}%")
            print(f"평가 레벨: {buffett_analysis.get('level', 'N/A')}")
            signal_type = buffett_analysis.get('signal_type')
            if signal_type:
                print(f"버핏 지수 신호: {signal_type} (신뢰도: {buffett_analysis.get('confidence', 0):.2f})")
            else:
                print("버핏 지수 신호: 중립")
        else:
            print("버핏 지수 분석 실패")
        
        # 결합된 시장 심리 분석
        print("\n3. 결합된 시장 심리 분석...")
        combined_analysis = analyzer.get_combined_market_sentiment()
        
        if combined_analysis:
            market_sentiment = combined_analysis.get('market_sentiment', 'UNKNOWN')
            print(f"시장 심리: {market_sentiment}")
            
            combined_signal = combined_analysis.get('combined_signal', {})
            if combined_signal.get('type'):
                print(f"결합 신호: {combined_signal['type']} (강도: {combined_signal.get('strength', 0):.1f}, 신뢰도: {combined_signal.get('confidence', 0):.2f})")
                print(f"신호 근거: {combined_signal.get('reason', 'N/A')}")
            else:
                print("결합 신호: 없음")
        else:
            print("결합된 분석 실패")
        
        print("\n=== VIX 분석 테스트 완료 ===")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vix_analysis() 