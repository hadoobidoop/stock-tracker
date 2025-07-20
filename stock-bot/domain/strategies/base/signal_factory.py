"""
TradingSignal 생성 팩토리 - 전략에서 사용하는 신호 생성 로직을 제공
"""

from datetime import datetime
from typing import Dict

import pandas as pd

from domain.signals.models.trading_signal import TradingSignal, SignalType
from infrastructure.db.models.enums import TrendType


class TradingSignalFactory:
    """TradingSignal 객체 생성을 담당하는 팩토리 클래스"""
    
    @staticmethod
    def create_trading_signal(signal_result: Dict, ticker: str, score: float,
                            df_with_indicators: pd.DataFrame, strategy_name: str) -> TradingSignal:
        """
        공통 TradingSignal 객체 생성 로직
        
        Args:
            signal_result: 신호 결과 딕셔너리
            ticker: 티커 심볼
            score: 신호 점수
            df_with_indicators: 지표가 포함된 데이터프레임
            strategy_name: 전략 이름
            
        Returns:
            TradingSignal: 생성된 거래 신호 객체
        """
        from domain.signals.models.trading_signal import SignalEvidence

        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL

        evidence = SignalEvidence(
            signal_timestamp=datetime.now(),
            ticker=ticker,
            signal_type=signal_result.get('type', 'BUY'),
            final_score=int(score),
            raw_signals=signal_result.get('details', []),
            applied_filters=[f"Strategy: {strategy_name}"],
            score_adjustments=[f"Strategy adjustment applied: {strategy_name}"]
        )

        return TradingSignal(
            signal_id=None,
            ticker=ticker,
            signal_type=signal_type,
            signal_score=int(score),
            timestamp_utc=datetime.now(),
            current_price=df_with_indicators['Close'].iloc[-1],
            market_trend=TrendType(signal_result.get('market_trend', 'NEUTRAL')),
            long_term_trend=TrendType(signal_result.get('long_term_trend', 'NEUTRAL')),
            details=signal_result.get('details', []),
            stop_loss_price=signal_result.get('stop_loss_price'),
            evidence=evidence
        )


class TradingSignalMixin:
    """TradingSignal 생성 기능을 제공하는 Mixin 클래스"""
    
    def _create_trading_signal(self, signal_result: Dict, ticker: str, score: float,
                             df_with_indicators: pd.DataFrame) -> TradingSignal:
        """
        TradingSignal 객체 생성 (Mixin 메서드)
        """
        return TradingSignalFactory.create_trading_signal(
            signal_result=signal_result,
            ticker=ticker,
            score=score,
            df_with_indicators=df_with_indicators,
            strategy_name=self.get_name()
        )