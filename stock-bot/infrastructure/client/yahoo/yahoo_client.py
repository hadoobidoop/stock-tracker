import pandas as pd
import yfinance as yf
import logging
from typing import List, Dict, Union, Tuple, Optional
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)

def get_ohlcv_data(
    symbols: Union[str, List[str]],
    period: str,
    interval: str,
) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
    """
    야후 파이낸스에서 OHLCV 데이터를 가져옵니다.

    Args:
        symbols (Union[str, List[str]]): 주식 티커 심볼 또는 심볼 리스트.
        period (str): 현재로부터의 기간 (예: '7d', '1mo', '1y').
        interval (str): 데이터 간격 (예: '1d', '1h', '1m').

    Returns:
        Tuple[Dict[str, pd.DataFrame], List[str]]:
            - 첫 번째 요소: 성공적으로 가져온 데이터. {'티커': DataFrame} 형식의 딕셔너리.
            - 두 번째 요소: 데이터를 가져오는 데 실패한 티커 리스트.
    """
    is_single_symbol = isinstance(symbols, str)
    symbols_list = [symbols] if is_single_symbol else symbols
    
    logger.info(f"Fetching {interval} OHLCV for {symbols_list} (period: {period}) from Yahoo Finance...")

    try:
        df_raw = yf.download(
            tickers=symbols_list,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            group_by='ticker' # 항상 티커별로 그룹화하여 멀티인덱스 반환
        )

        if df_raw.empty:
            logger.warning("No data returned from yfinance for the given parameters.")
            return {}, symbols_list

        successful_data = {}
        failed_tickers = []

        for ticker in symbols_list:
            # yfinance는 실패한 티커에 대한 컬럼을 생성하지 않거나, 데이터가 모두 NaN일 수 있음
            if ticker not in df_raw.columns.get_level_values(0):
                logger.warning(f"Ticker '{ticker}' not found in yfinance response.")
                failed_tickers.append(ticker)
                continue

            df_symbol = df_raw[ticker].copy()
            df_symbol.dropna(how='all', inplace=True)

            if df_symbol.empty:
                logger.warning(f"No valid data for ticker '{ticker}' after dropping NaN values.")
                failed_tickers.append(ticker)
                continue
            
            # 컬럼명 정규화 및 타임존 통일
            df_symbol.columns = [str(col).capitalize() for col in df_symbol.columns]
            
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df_symbol.columns for col in required_cols):
                logger.error(f"Missing required columns for {ticker}. Available: {df_symbol.columns.tolist()}")
                failed_tickers.append(ticker)
                continue

            # 타임존이 없으면 UTC로 설정, 있으면 UTC로 변환
            if df_symbol.index.tz is None:
                df_symbol.index = df_symbol.index.tz_localize('UTC')
            else:
                df_symbol.index = df_symbol.index.tz_convert('UTC')

            successful_data[ticker] = df_symbol[required_cols]
            logger.info(f"Successfully processed {len(df_symbol)} rows for {ticker}.")
        
        return successful_data, failed_tickers

    except Exception as e:
        logger.error(f"An unexpected error occurred during yfinance download: {e}", exc_info=True)
        return {}, symbols_list
