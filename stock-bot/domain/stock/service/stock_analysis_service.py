from typing import List, Dict, Tuple
import pandas as pd
from datetime import datetime
from pytz import timezone

from infrastructure.logging import get_logger
from infrastructure.client.yahoo import get_ohlcv_data
from infrastructure.db.models.enums import TrendType
from domain.stock.repository.stock_repository import StockRepository
from domain.stock.models.stock_metadata import StockMetadata
from domain.stock.config.settings import STOCK_SYMBOLS
from domain.analysis.config.analysis_settings import REALTIME_SIGNAL_DETECTION

logger = get_logger(__name__)


class StockAnalysisService:
    """주식 분석 관련 서비스"""
    
    def __init__(self, stock_repository: StockRepository):
        self.stock_repository = stock_repository
    
    def get_current_et_time(self) -> datetime:
        """현재 미국 동부 시간을 반환합니다."""
        et_tz = timezone('US/Eastern')
        return datetime.now(et_tz)
    
    def get_stocks_to_analyze(self) -> List[str]:
        """분석할 주식 목록을 반환합니다."""
        try:
            # Repository를 통해 분석 대상 주식 조회
            stocks = self.stock_repository.get_stocks_for_analysis()
            return [stock.ticker for stock in stocks]
        except Exception as e:
            logger.error(f"Error getting stocks to analyze: {e}")
            return STOCK_SYMBOLS
    
    def get_market_trend(self, market_data: pd.DataFrame = None) -> TrendType:
        """
        시장 추세를 판단합니다.
        
        Args:
            market_data: 백테스팅용 시장 데이터 (제공되지 않으면 실시간 데이터 조회)
        """
        try:
            sma_period = REALTIME_SIGNAL_DETECTION["MARKET_TREND_SMA_PERIOD"]
            
            if market_data is None:
                market_symbol = REALTIME_SIGNAL_DETECTION["MARKET_INDEX_SYMBOL"]
                data, _ = get_ohlcv_data(market_symbol, f"{sma_period}d", '1d')
                df_market = data.get(market_symbol)
            else:
                df_market = market_data

            if df_market is not None and not df_market.empty and len(df_market) >= sma_period:
                df_market[f'SMA_{sma_period}'] = df_market['Close'].rolling(window=sma_period).mean()
                latest_close = df_market.iloc[-1]['Close']
                latest_sma = df_market.iloc[-1][f'SMA_{sma_period}']
                
                if not pd.isna(latest_sma):
                    if latest_close > latest_sma:
                        return TrendType.BULLISH
                    elif latest_close < latest_sma:
                        return TrendType.BEARISH
            
            return TrendType.NEUTRAL
        except Exception as e:
            logger.error(f"Error determining market trend: {e}")
            return TrendType.NEUTRAL
    
    def get_long_term_trend(self, df: pd.DataFrame) -> Tuple[TrendType, Dict]:
        """장기 추세를 판단합니다."""
        try:
            sma_period = REALTIME_SIGNAL_DETECTION["LONG_TERM_TREND_SMA_PERIOD"]
            
            if df is None or df.empty or len(df) < sma_period:
                return TrendType.NEUTRAL, {}
            
            df[f'SMA_{sma_period}'] = df['Close'].rolling(window=sma_period).mean()
            latest_close = df.iloc[-1]['Close']
            latest_sma = df.iloc[-1][f'SMA_{sma_period}']
            
            if pd.isna(latest_sma):
                return TrendType.NEUTRAL, {}
            
            trend = TrendType.BULLISH if latest_close > latest_sma else TrendType.BEARISH
            trend_values = {
                'close': latest_close,
                'sma': latest_sma,
                'sma_period': sma_period
            }
            
            return trend, trend_values
        except Exception as e:
            logger.error(f"Error calculating long term trend: {e}")
            return TrendType.NEUTRAL, {}
    
    def get_stock_data_for_analysis(self, symbols: List[str], lookback_days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """분석용 주식 데이터를 조회합니다."""
        try:
            data, _ = get_ohlcv_data(symbols, f"{lookback_days}d", interval)
            return data
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
            return {} 