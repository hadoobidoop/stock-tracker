from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class CompositeSignalDetector(SignalDetector):
    """여러 감지기를 조합한 복합 신호 감지기"""
    
    def __init__(self, detectors: List[SignalDetector], weight: float, require_all: bool = False, name: str = None):
        super().__init__(weight, name or "Composite_Detector")
        self.detectors = detectors
        self.require_all = require_all  # True: 모든 감지기가 신호를 감지해야 함, False: 하나라도 감지하면 됨
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """복합 신호를 감지합니다."""
        
        if not self.detectors:
            return 0.0, 0.0, [], []
        
        all_buy_signals = []
        all_sell_signals = []
        all_buy_details = []
        all_sell_details = []
        
        # 각 감지기로부터 신호 수집
        for detector in self.detectors:
            try:
                buy_score, sell_score, buy_details, sell_details = detector.detect_signals(
                    df, market_trend, long_term_trend, daily_extra_indicators
                )
                
                if buy_score > 0:
                    all_buy_signals.append(buy_score)
                    all_buy_details.extend(buy_details)
                
                if sell_score > 0:
                    all_sell_signals.append(sell_score)
                    all_sell_details.extend(sell_details)
                    
            except Exception as e:
                logger.error(f"Error in composite detector {detector.name}: {e}")
                continue
        
        # 복합 신호 판단
        final_buy_score = 0.0
        final_sell_score = 0.0
        
        if self.require_all:
            # 모든 감지기가 신호를 감지해야 함
            if len(all_buy_signals) == len(self.detectors):
                final_buy_score = self.weight
            if len(all_sell_signals) == len(self.detectors):
                final_sell_score = self.weight
        else:
            # 하나라도 감지하면 됨
            if all_buy_signals:
                final_buy_score = self.weight
            if all_sell_signals:
                final_sell_score = self.weight
        
        return final_buy_score, final_sell_score, all_buy_details, all_sell_details