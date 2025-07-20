"""
Repository 팩토리 패턴
Centralized repository creation and management
"""
from typing import Optional
from domain.signals.repository.technical_indicator_repository import TechnicalIndicatorRepository
from domain.signals.repository.trading_signal_repository import TradingSignalRepository
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_technical_indicator_repository import SQLTechnicalIndicatorRepository
from infrastructure.db.repository.sql_trading_signal_repository import SQLTradingSignalRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class RepositoryFactory:
    """Repository 인스턴스 생성 및 관리"""
    
    _technical_indicator_repo: Optional[TechnicalIndicatorRepository] = None
    _trading_signal_repo: Optional[TradingSignalRepository] = None
    _stock_repo: Optional[StockRepository] = None
    
    @classmethod
    def get_technical_indicator_repository(cls) -> TechnicalIndicatorRepository:
        """기술적 지표 repository 인스턴스 반환 (싱글톤)"""
        if cls._technical_indicator_repo is None:
            cls._technical_indicator_repo = SQLTechnicalIndicatorRepository()
            logger.debug("Technical indicator repository instance created")
        return cls._technical_indicator_repo
    
    @classmethod
    def get_trading_signal_repository(cls) -> TradingSignalRepository:
        """거래 신호 repository 인스턴스 반환 (싱글톤)"""
        if cls._trading_signal_repo is None:
            cls._trading_signal_repo = SQLTradingSignalRepository()
            logger.debug("Trading signal repository instance created")
        return cls._trading_signal_repo
    
    @classmethod
    def get_stock_repository(cls) -> StockRepository:
        """주식 repository 인스턴스 반환 (싱글톤)"""
        if cls._stock_repo is None:
            cls._stock_repo = SQLStockRepository()
            logger.debug("Stock repository instance created")
        return cls._stock_repo
    
    @classmethod
    def reset_repositories(cls):
        """Repository 인스턴스 초기화 (테스트용)"""
        cls._technical_indicator_repo = None
        cls._trading_signal_repo = None
        cls._stock_repo = None
        logger.debug("All repository instances reset")


class IndicatorPersistenceService:
    """기술적 지표 저장 서비스"""
    
    def __init__(self):
        self.repo = RepositoryFactory.get_technical_indicator_repository()
    
    def save_latest_indicators(self, df_with_indicators, symbol: str, timeframe: str) -> bool:
        """
        최신 기술적 지표 저장
        
        Args:
            df_with_indicators: 지표가 포함된 DataFrame
            symbol: 종목 심볼
            timeframe: 시간프레임 ('1d', '1h' 등)
        
        Returns:
            저장 성공 여부
        """
        try:
            from .data_processing_utils import IndicatorColumnFilter
            
            # 기술적 지표만 필터링
            latest_indicators = IndicatorColumnFilter.get_latest_indicators(df_with_indicators)
            
            if latest_indicators.empty:
                logger.warning(f"No indicators to save for {symbol}")
                return False
            
            # Repository를 통해 저장
            self.repo.save_indicators(latest_indicators, symbol, timeframe)
            
            indicator_count = len(IndicatorColumnFilter.get_indicator_columns(df_with_indicators))
            logger.info(f"Successfully saved/updated {indicator_count} technical indicators for {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save indicators for {symbol}: {e}")
            return False