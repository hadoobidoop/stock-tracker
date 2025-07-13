from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from domain.analysis.config.signal_adjustment_factors import SIGNAL_ADJUSTMENT_FACTORS_BY_TREND


class SignalDetector(ABC):
    """신호 감지기의 기본 추상 클래스"""
    
    def __init__(self, weight: float, name: str = None):
        self.weight = weight
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """
        신호를 감지하고 점수를 반환합니다.
        
        Args:
            df: OHLCV 및 지표 데이터가 포함된 DataFrame
            market_trend: 시장 추세
            long_term_trend: 장기 추세
            daily_extra_indicators: 일봉 추가 지표 (피봇, 피보나치 등)
            
        Returns:
            Tuple[float, float, List[str], List[str]]: (매수점수, 매도점수, 매수상세, 매도상세)
        """
        pass
    
    def get_adjustment_factor(self, market_trend: TrendType, factor_type: str) -> float:
        """시장 추세에 따른 조정 계수를 반환합니다."""
        
        adjustment_factors = SIGNAL_ADJUSTMENT_FACTORS_BY_TREND.get(market_trend.value, {})
        return adjustment_factors.get(factor_type, 1.0)
    
    def validate_required_columns(self, df: pd.DataFrame, required_columns: List[str]) -> bool:
        """필수 컬럼들이 DataFrame에 존재하고 유효한지 검증합니다."""
        if df.empty:
            return False
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False
        
        # 최소 2개의 행이 있는지 확인 (현재와 이전 데이터 비교용)
        if len(df) < 2:
            return False
        
        return True
    
    def validate_required_columns(self, df: pd.DataFrame, required_prefixes: List[str]) -> bool:
        """필요한 컬럼들이 DataFrame에 존재하는지 확인합니다."""
        current_cols = df.columns
        
        for prefix in required_prefixes:
            if prefix not in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if not any(col.startswith(prefix) for col in current_cols):
                    return False
            elif prefix not in current_cols:
                return False
        
        return True 