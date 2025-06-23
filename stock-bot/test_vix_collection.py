#!/usr/bin/env python3
"""
VIX 데이터 수집 테스트 스크립트
"""
import sys
import os
sys.path.append(os.getcwd())

from infrastructure.logging import setup_logging
from domain.stock.service.market_data_service import MarketDataService

def test_vix_collection():
    """VIX 데이터 수집 테스트"""
    setup_logging()
    
    print("=== VIX 데이터 수집 테스트 시작 ===")
    
    try:
        service = MarketDataService()
        
        # VIX 데이터 업데이트
        print("1. VIX 데이터 수집 중...")
        vix_success = service.update_vix()
        print(f"VIX 수집 결과: {'성공' if vix_success else '실패'}")
        
        # 버핏 지수 데이터 업데이트
        print("2. 버핏 지수 데이터 수집 중...")
        buffett_success = service.update_buffett_indicator()
        print(f"버핏 지수 수집 결과: {'성공' if buffett_success else '실패'}")
        
        # 10년 국채 수익률 데이터 업데이트
        print("3. 10년 국채 수익률 데이터 수집 중...")
        treasury_success = service.update_treasury_yield()
        print(f"10년 국채 수익률 수집 결과: {'성공' if treasury_success else '실패'}")
        
        # 최신 데이터 확인
        print("\n=== 수집된 데이터 확인 ===")
        latest_vix = service.get_latest_vix()
        latest_buffett = service.get_latest_buffett_indicator()
        latest_treasury = service.get_latest_treasury_yield()
        
        if latest_vix:
            print(f"최신 VIX: {latest_vix:.2f}")
        else:
            print("VIX 데이터 없음")
            
        if latest_buffett:
            print(f"최신 버핏 지수: {latest_buffett:.2f}%")
        else:
            print("버핏 지수 데이터 없음")
            
        if latest_treasury:
            print(f"최신 10년 국채 수익률: {latest_treasury:.2f}%")
        else:
            print("10년 국채 수익률 데이터 없음")
        
        print("\n=== VIX 분석 테스트 ===")
        from domain.analysis.utils.market_indicators import MarketIndicatorAnalyzer
        
        analyzer = MarketIndicatorAnalyzer()
        vix_analysis = analyzer.get_vix_analysis()
        
        if vix_analysis:
            print(f"현재 VIX: {vix_analysis.get('current_vix', 'N/A')}")
            print(f"공포 레벨: {vix_analysis.get('fear_level', 'N/A')}")
            print(f"VIX 트렌드: {vix_analysis.get('trend', 'N/A')}")
            
            trading_signal = vix_analysis.get('trading_signal', {})
            if trading_signal.get('type'):
                print(f"거래 신호: {trading_signal['type']} (강도: {trading_signal.get('strength', 0):.1f})")
            else:
                print("거래 신호: 없음")
        else:
            print("VIX 분석 실패")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vix_collection() 