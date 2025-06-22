#!/usr/bin/env python3
"""
매수매도 신호 근거 분석 테스트 스크립트

이 스크립트는 새로 구현된 상세한 매수매도 근거 저장 시스템을 테스트합니다.
실제 저장된 신호의 근거를 분석하고 시각화하는 기능을 제공합니다.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

from infrastructure.logging import get_logger
from infrastructure.db.repository.sql_trading_signal_repository import SQLTradingSignalRepository
from domain.analysis.models.trading_signal import SignalEvidence

logger = get_logger(__name__)

def analyze_signal_evidence(ticker: str = None, days_back: int = 7) -> None:
    """
    저장된 신호의 근거를 분석합니다.
    
    Args:
        ticker: 분석할 종목 (None이면 모든 종목)
        days_back: 몇 일 전까지의 데이터를 분석할지
    """
    print("🔍 매수매도 신호 근거 분석 시작")
    print("=" * 60)
    
    repo = SQLTradingSignalRepository()
    
    # 분석 기간 설정
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    print(f"📅 분석 기간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"🎯 대상 종목: {ticker if ticker else '전체'}")
    print()
    
    # 신호 조회
    if ticker:
        signals = repo.get_signals_by_ticker(ticker, start_time, end_time)
    else:
        # 전체 신호 조회 (임시로 몇 개 종목만)
        all_signals = []
        for test_ticker in ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']:
            ticker_signals = repo.get_signals_by_ticker(test_ticker, start_time, end_time)
            all_signals.extend(ticker_signals)
        signals = all_signals
    
    if not signals:
        print("❌ 해당 기간에 저장된 신호가 없습니다.")
        return
    
    print(f"📊 총 {len(signals)}개의 신호를 찾았습니다.")
    print()
    
    # 신호별 상세 근거 분석
    buy_signals = [s for s in signals if s.signal_type.value == 'BUY']
    sell_signals = [s for s in signals if s.signal_type.value == 'SELL']
    
    print(f"📈 매수 신호: {len(buy_signals)}개")
    print(f"📉 매도 신호: {len(sell_signals)}개")
    print()
    
    # 가장 최근 신호들의 상세 근거 분석
    recent_signals = sorted(signals, key=lambda x: x.timestamp_utc, reverse=True)[:5]
    
    for i, signal in enumerate(recent_signals, 1):
        print(f"🔍 신호 #{i}: {signal.ticker} {signal.signal_type.value}")
        print(f"   시간: {signal.timestamp_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   점수: {signal.signal_score}")
        print(f"   가격: ${signal.current_price:.2f}")
        
        if signal.evidence:
            analyze_individual_evidence(signal.evidence)
        else:
            print("   ⚠️ 상세 근거 없음 (구버전 신호)")
        
        print("-" * 40)


def analyze_individual_evidence(evidence: SignalEvidence) -> None:
    """개별 신호의 근거를 상세 분석합니다."""
    
    # 1. 기술적 지표 근거 분석
    if evidence.technical_evidences:
        print(f"   📊 기술적 지표 근거 ({len(evidence.technical_evidences)}개):")
        for te in evidence.technical_evidences:
            print(f"      • {te.indicator_name}: {te.condition_met}")
            if te.current_value is not None:
                print(f"        현재값: {te.current_value:.3f}")
            if te.contribution_score > 0:
                print(f"        기여도: {te.contribution_score:.1f}")
    
    # 2. 다중 시간대 분석 근거
    if evidence.multi_timeframe_evidence:
        mte = evidence.multi_timeframe_evidence
        print(f"   ⏰ 다중 시간대 분석:")
        print(f"      일봉 추세: {mte.daily_trend}")
        print(f"      시간봉 추세: {mte.hourly_trend}")
        print(f"      종합 판단: {mte.consensus}")
        print(f"      신뢰도 조정: {mte.confidence_adjustment:.2f}")
        
        if mte.daily_indicators:
            print(f"      일봉 지표: {format_indicators(mte.daily_indicators)}")
        if mte.hourly_indicators:
            print(f"      시간봉 지표: {format_indicators(mte.hourly_indicators)}")
    
    # 3. 시장 상황 근거
    if evidence.market_context_evidence:
        mce = evidence.market_context_evidence
        print(f"   🏦 시장 상황:")
        print(f"      시장 추세: {mce.market_trend}")
        if mce.volatility_level:
            print(f"      변동성: {mce.volatility_level}")
        if mce.volume_analysis:
            print(f"      거래량: {mce.volume_analysis}")
    
    # 4. 리스크 관리 근거
    if evidence.risk_management_evidence:
        rme = evidence.risk_management_evidence
        print(f"   🛡️ 리스크 관리:")
        print(f"      손절 방법: {rme.stop_loss_method}")
        print(f"      손절 비율: {rme.stop_loss_percentage:.2f}%")
        if rme.risk_reward_ratio:
            print(f"      위험대비수익: {rme.risk_reward_ratio:.2f}:1")
    
    # 5. 의사결정 과정
    if evidence.raw_signals:
        print(f"   🎯 원시 신호: {', '.join(evidence.raw_signals[:3])}...")
    
    if evidence.applied_filters:
        print(f"   🔍 적용 필터: {', '.join(evidence.applied_filters)}")
    
    if evidence.score_adjustments:
        print(f"   ⚖️ 점수 조정: {', '.join(evidence.score_adjustments)}")


def format_indicators(indicators: Dict[str, float]) -> str:
    """지표 딕셔너리를 보기 좋은 문자열로 포맷팅합니다."""
    if not indicators:
        return "없음"
    
    formatted = []
    for name, value in list(indicators.items())[:3]:  # 최대 3개만 표시
        formatted.append(f"{name}={value:.2f}")
    
    return ", ".join(formatted)


def generate_evidence_report(ticker: str, days_back: int = 30) -> Dict[str, Any]:
    """
    특정 종목의 신호 근거 통계 리포트를 생성합니다.
    
    Returns:
        Dict: 통계 정보가 담긴 딕셔너리
    """
    repo = SQLTradingSignalRepository()
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    signals = repo.get_signals_by_ticker(ticker, start_time, end_time)
    
    if not signals:
        return {"error": "신호 없음"}
    
    # 통계 계산
    total_signals = len(signals)
    buy_signals = len([s for s in signals if s.signal_type.value == 'BUY'])
    sell_signals = len([s for s in signals if s.signal_type.value == 'SELL'])
    
    # 근거가 있는 신호 비율
    signals_with_evidence = len([s for s in signals if s.evidence])
    evidence_ratio = signals_with_evidence / total_signals if total_signals > 0 else 0
    
    # 평균 신호 점수
    avg_score = sum(s.signal_score for s in signals) / total_signals if total_signals > 0 else 0
    
    # 가장 많이 사용된 기술적 지표
    indicator_usage = {}
    for signal in signals:
        if signal.evidence and signal.evidence.technical_evidences:
            for te in signal.evidence.technical_evidences:
                indicator_usage[te.indicator_name] = indicator_usage.get(te.indicator_name, 0) + 1
    
    # 다중 시간대 분석 사용률
    mt_analysis_count = len([s for s in signals if s.evidence and s.evidence.multi_timeframe_evidence])
    mt_analysis_ratio = mt_analysis_count / total_signals if total_signals > 0 else 0
    
    return {
        "ticker": ticker,
        "period_days": days_back,
        "total_signals": total_signals,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "evidence_ratio": evidence_ratio,
        "avg_score": avg_score,
        "top_indicators": sorted(indicator_usage.items(), key=lambda x: x[1], reverse=True)[:5],
        "multi_timeframe_usage": mt_analysis_ratio
    }


if __name__ == "__main__":
    print("🚀 매수매도 근거 분석 시스템 테스트")
    print()
    
    # 1. 기본 근거 분석
    analyze_signal_evidence(ticker="AAPL", days_back=7)
    
    print("\n" + "="*60 + "\n")
    
    # 2. 통계 리포트 생성
    print("📈 신호 근거 통계 리포트")
    report = generate_evidence_report("AAPL", days_back=30)
    
    if "error" not in report:
        print(f"종목: {report['ticker']}")
        print(f"기간: {report['period_days']}일")
        print(f"총 신호: {report['total_signals']}개")
        print(f"매수/매도: {report['buy_signals']}개/{report['sell_signals']}개")
        print(f"근거 포함율: {report['evidence_ratio']:.1%}")
        print(f"평균 점수: {report['avg_score']:.1f}")
        print(f"다중시간대 사용률: {report['multi_timeframe_usage']:.1%}")
        
        if report['top_indicators']:
            print("주요 지표:")
            for indicator, count in report['top_indicators']:
                print(f"  • {indicator}: {count}회 사용")
    else:
        print(f"⚠️ {report['error']}")
    
    print("\n✅ 근거 분석 시스템 테스트 완료!") 