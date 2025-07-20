"""
공통 데이터 처리 유틸리티
Shared data processing utilities for signal detection services
"""
from typing import Optional, List, Dict, Any
import pandas as pd
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DataFrameValidator:
    """DataFrame 유효성 검사 유틸리티"""
    
    @staticmethod
    def is_valid_dataframe(df: Optional[pd.DataFrame], min_length: int = 1) -> bool:
        """DataFrame 유효성 검사"""
        return df is not None and not df.empty and len(df) >= min_length
    
    @staticmethod
    def validate_for_indicators(df: Optional[pd.DataFrame], min_length: int = 60) -> bool:
        """기술적 지표 계산을 위한 DataFrame 유효성 검사"""
        if not DataFrameValidator.is_valid_dataframe(df, min_length):
            return False
        
        # 필수 컬럼 확인
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        return all(col in df.columns for col in required_columns)


class IndicatorColumnFilter:
    """기술적 지표 컬럼 필터링 유틸리티"""
    
    EXCLUDED_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    @classmethod
    def get_indicator_columns(cls, df: pd.DataFrame) -> List[str]:
        """기술적 지표 컬럼만 반환"""
        return [col for col in df.columns if col not in cls.EXCLUDED_COLUMNS]
    
    @classmethod
    def filter_indicators_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 컬럼만 포함된 DataFrame 반환"""
        indicator_columns = cls.get_indicator_columns(df)
        return df[indicator_columns].copy()
    
    @classmethod
    def get_latest_indicators(cls, df: pd.DataFrame) -> pd.DataFrame:
        """최신 시점의 기술적 지표만 반환"""
        indicator_df = cls.filter_indicators_dataframe(df)
        return indicator_df.iloc[-1:].copy()


class DataProcessingHelper:
    """데이터 처리 헬퍼 클래스"""
    
    @staticmethod
    def safe_execute_with_logging(
        operation_name: str,
        symbol: str,
        operation_func,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Any:
        """
        안전한 작업 실행 with 로깅
        
        Args:
            operation_name: 작업 이름
            symbol: 종목 심볼
            operation_func: 실행할 함수
            success_message: 성공 메시지 (optional)
            error_message: 에러 메시지 (optional)
        
        Returns:
            작업 결과 또는 None (실패시)
        """
        try:
            result = operation_func()
            
            if success_message:
                logger.debug(success_message.format(symbol=symbol))
            else:
                logger.debug(f"{symbol} {operation_name} 완료")
                
            return result
            
        except Exception as e:
            if error_message:
                logger.error(error_message.format(symbol=symbol, error=e))
            else:
                logger.error(f"{symbol} {operation_name} 실패: {e}")
            return None
    
    @staticmethod
    def validate_and_process_dataframe(
        df: Optional[pd.DataFrame],
        symbol: str,
        operation_name: str,
        min_length: int = 1
    ) -> Optional[pd.DataFrame]:
        """DataFrame 유효성 검사 및 처리"""
        
        if not DataFrameValidator.is_valid_dataframe(df, min_length):
            logger.warning(f"{symbol}의 {operation_name}을 위한 데이터가 부족합니다: "
                          f"length={len(df) if df is not None else 0}, required={min_length}")
            return None
            
        return df


class IndicatorCalculationService:
    """기술적 지표 계산 서비스"""
    
    @staticmethod
    def calculate_with_validation(
        df: Optional[pd.DataFrame],
        symbol: str,
        calculator_func,
        min_length: int = 60
    ) -> Optional[pd.DataFrame]:
        """
        유효성 검사를 포함한 기술적 지표 계산
        
        Args:
            df: 입력 DataFrame
            symbol: 종목 심볼
            calculator_func: 지표 계산 함수
            min_length: 최소 데이터 길이
        
        Returns:
            계산된 지표가 포함된 DataFrame 또는 None
        """
        # 데이터 유효성 검사
        validated_df = DataProcessingHelper.validate_and_process_dataframe(
            df, symbol, "기술적 지표 계산", min_length
        )
        
        if validated_df is None:
            return None
        
        # 안전한 지표 계산 실행
        return DataProcessingHelper.safe_execute_with_logging(
            operation_name="기술적 지표 계산",
            symbol=symbol,
            operation_func=lambda: calculator_func(validated_df),
            success_message=f"{{symbol}} 기술적 지표 계산 완료: {len(validated_df)} bars"
        )