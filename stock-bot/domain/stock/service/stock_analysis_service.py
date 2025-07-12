from typing import List, Dict, Tuple
import pandas as pd
from datetime import datetime
from pytz import timezone
from dataclasses import dataclass, field

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType
from domain.stock.repository.stock_repository import StockRepository
from domain.stock.models.stock_metadata import StockMetadata
from domain.stock.config.settings import STOCK_SYMBOLS
from domain.analysis.config.signals import REALTIME_SIGNAL_DETECTION

logger = get_logger(__name__)


@dataclass
class TrendAnalysisResult:
    """추세 분석 결과를 담는 데이터 클래스"""
    trend: TrendType = TrendType.NEUTRAL
    values: Dict = field(default_factory=dict)


class StockAnalysisService:
    """주식 분석 관련 서비스"""
    
    def __init__(self, stock_repository: StockRepository):
        self.stock_repository = stock_repository
    
    def get_current_et_time(self) -> datetime:
        """현재 미국 동부 시간을 반환합니다."""
        et_tz = timezone('US/Eastern')
        return datetime.now(et_tz)
    
    def get_stocks_to_analyze(self) -> List[str]:
        """분석할 모든 주식 목록을 DB에서 조회하여 반환합니다."""
        all_stocks = []
        page = 1
        page_size = 100

        try:
            while True:
                stocks = self.stock_repository.get_stocks_for_analysis(page=page, page_size=page_size)
                if not stocks:
                    break
                all_stocks.extend(stocks)
                page += 1
            
            if not all_stocks:
                logger.warning("No stocks for analysis found in DB, falling back to STOCK_SYMBOLS.")
                return STOCK_SYMBOLS

            return [stock.ticker for stock in all_stocks]
        except Exception as e:
            logger.error(f"Error getting stocks to analyze: {e}", exc_info=True)
            logger.warning("Falling back to STOCK_SYMBOLS due to an error.")
            return STOCK_SYMBOLS

    def _calculate_trend_from_sma(self, df: pd.DataFrame, sma_period: int) -> TrendAnalysisResult:
        """
        주어진 DataFrame과 이동평균선(SMA) 기간을 기반으로 추세를 계산하는 내부 헬퍼 메서드.
        이 메서드는 TrendType과 함께, 판단의 근거가 된 상세 값들을 TrendAnalysisResult 객체로 반환합니다.

        Args:
            df (pd.DataFrame): 'Close' 컬럼을 포함하는 시계열 데이터.
            sma_period (int): 추세 판단에 사용할 이동평균선 기간.

        Returns:
            TrendAnalysisResult: 추세 분석 결과(trend, values)를 담은 데이터 객체.
        """
        if df is None or df.empty or len(df) < sma_period:
            return TrendAnalysisResult()

        try:
            df = df.copy()
            sma_col = f'SMA_{sma_period}'
            df[sma_col] = df['Close'].rolling(window=sma_period).mean()
            
            latest_row = df.iloc[-1]
            latest_close = latest_row['Close']
            latest_sma = latest_row[sma_col]
            
            if pd.isna(latest_sma):
                return TrendAnalysisResult()

            trend = TrendType.BULLISH if latest_close > latest_sma else TrendType.BEARISH
            trend_values = {
                'close': latest_close,
                'sma': latest_sma,
                'sma_period': sma_period
            }
            return TrendAnalysisResult(trend=trend, values=trend_values)
        except Exception as e:
            logger.error(f"Error during SMA trend calculation for period {sma_period}: {e}")
            return TrendAnalysisResult()

    def get_market_trend(self, market_data: pd.DataFrame = None) -> TrendType:
        """
        시장 전체의 단기 추세(예: 50일)를 판단합니다. (숲의 방향)
        이 메서드는 모든 개별 주식 분석에 공통적으로 적용될 거시적인 시장 상황을 파악하기 위해 사용됩니다.
        
        참고: 이 메서드는 DB 조회를 포함할 수 있으므로, 전체 분석 시작 시 한 번만 호출하여 그 결과를 재사용하는 것이 효율적입니다.

        Args:
            market_data (pd.DataFrame, optional): 백테스팅 시 사용할 시장 지수 데이터. 
                                                  제공되지 않으면 설정된 심볼(예: ^GSPC)로 DB에서 직접 조회합니다.

        Returns:
            TrendType: 시장의 전반적인 추세 (BULLISH, BEARISH, NEUTRAL).
        """
        sma_period = REALTIME_SIGNAL_DETECTION["MARKET_TREND_SMA_PERIOD"]
        
        if market_data is None:
            market_symbol = REALTIME_SIGNAL_DETECTION["MARKET_INDEX_SYMBOL"]
            # 시장 전체의 추세를 보기 위해 대표 지수 데이터를 조회합니다.
            df_market = self.stock_repository.get_ohlcv_data_from_db(
                tickers=[market_symbol], days=sma_period + 5, interval='1d'
            ).get(market_symbol)
        else:
            df_market = market_data
            
        result = self._calculate_trend_from_sma(df_market, sma_period)
        return result.trend

    def get_long_term_trend(self, df: pd.DataFrame) -> TrendAnalysisResult:
        """
        개별 주식의 장기 추세(예: 120일)를 판단합니다. (개별 나무의 상태)
        이 메서드는 특정 주식 하나가 장기적으로 어떤 흐름을 보이는지 파악하기 위해 사용됩니다.

        Args:
            df (pd.DataFrame): 분석할 개별 주식의 시계열 데이터. 반드시 외부에서 주입되어야 합니다.

        Returns:
            TrendAnalysisResult: 추세의 방향과 함께, 판단 근거가 된 상세 값(종가, SMA 값 등)을 포함한 데이터 객체를 반환합니다.
        """
        sma_period = REALTIME_SIGNAL_DETECTION["LONG_TERM_TREND_SMA_PERIOD"]
        return self._calculate_trend_from_sma(df, sma_period)
    
    def get_stock_data_for_analysis(self, symbols: List[str], lookback_days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """분석용 주식 데이터를 DB에서 조회합니다."""
        try:
            return self.stock_repository.get_ohlcv_data_from_db(
                tickers=symbols,
                days=lookback_days,
                interval=interval
            )
        except Exception as e:
            logger.error(f"Error fetching stock data from DB: {e}")
            return {}
 