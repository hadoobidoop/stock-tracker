# data_collector.py

import yfinance as yf
import logging
import pandas as pd
from datetime import datetime, timedelta
import ast # ast 모듈 임포트
from typing import Union, List, Dict # 타입 힌트를 위해 Union, List, Dict 임포트

logger = logging.getLogger(__name__)

def get_ohlcv_data(symbols: Union[str, List[str]], period: str, interval: str) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    야후 파이낸스에서 OHLCV 데이터를 가져옵니다. 단일 종목 또는 여러 종목을 지원합니다.

    Args:
        symbols (Union[str, List[str]]): 주식 티커 심볼 (예: 'AAPL') 또는 심볼 리스트 (예: ['AAPL', 'MSFT']).
        period (str): 데이터 기간 (yfinance 형식, 예: '7d', '1y').
        interval (str): 데이터 간격 (yfinance 형식, 예: '1d' (일봉), '1m' (1분봉)).

    Returns:
        Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
            단일 종목 요청 시 OHLCV 데이터를 담은 DataFrame.
            여러 종목 요청 시 각 종목별 OHLCV DataFrame을 담은 딕셔너리.
            데이터를 가져오지 못하면 빈 DataFrame 또는 빈 딕셔너리 반환.
    """
    is_single_symbol = isinstance(symbols, str)
    symbols_list = [symbols] if is_single_symbol else symbols

    logger.info(f"Fetching {interval} OHLCV data for {symbols_list} for period {period} from Yahoo Finance...")

    all_data_dict = {} # 여러 종목 데이터를 저장할 딕셔너리

    try:
        # yfinance.download()는 요청된 기간과 간격에 맞는 데이터를 DataFrame으로 반환
        # 여러 심볼을 요청하면 멀티인덱스 컬럼을 가진 DataFrame을 반환합니다.
        df_raw = yf.download(symbols_list, period=period, interval=interval, progress=False, auto_adjust=False)

        if not isinstance(df_raw, pd.DataFrame) or df_raw.empty:
            logger.warning(f"No data fetched or invalid data format for {symbols_list} with period {period} and interval {interval}. Returned type: {type(df_raw)}.")
            return pd.DataFrame() if is_single_symbol else {}

        # --- 멀티인덱스 또는 문자열 튜플 컬럼 처리 로직 강화 ---
        # yfinance가 단일 종목에 대해 멀티인덱스를 반환하는 경우도 있으므로, 항상 멀티인덱스 여부를 확인
        if isinstance(df_raw.columns, pd.MultiIndex):
            # 멀티인덱스 DataFrame을 각 종목별 DataFrame으로 분리
            for ticker in symbols_list:
                try:
                    # 특정 종목의 모든 컬럼 선택 (예: ('Open', 'AAPL'), ('High', 'AAPL') 등)
                    # .loc[:, (slice(None), ticker)] 는 모든 첫 번째 레벨 인덱스와 특정 티커를 선택
                    df_symbol = df_raw.loc[:, (slice(None), ticker)]
                    df_symbol.columns = [col[0] for col in df_symbol.columns] # 컬럼명을 첫 번째 레벨로 단일화

                    # 컬럼명 통일 (첫 글자 대문자)
                    df_symbol.columns = [str(col).capitalize() for col in df_symbol.columns]

                    # DatetimeIndex 확인 및 정렬
                    if not isinstance(df_symbol.index, pd.DatetimeIndex):
                        df_symbol.index = pd.to_datetime(df_symbol.index)
                    df_symbol.sort_index(inplace=True)

                    # 필요한 컬럼만 유지
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    for col in required_cols:
                        if col not in df_symbol.columns:
                            logger.error(f"Missing required column '{col}' for {ticker} from Yahoo Finance data. Available columns: {df_symbol.columns.tolist()}")
                            df_symbol = pd.DataFrame() # 누락 시 해당 종목 데이터 비움
                            break # 이 종목은 더 이상 처리하지 않음

                    if not df_symbol.empty:
                        all_data_dict[ticker] = df_symbol
                        logger.info(f"Successfully fetched {len(df_symbol)} rows of {interval} data for {ticker}.")
                    else:
                        logger.warning(f"No valid data remaining for {ticker} after column check.")

                except KeyError as ke:
                    logger.warning(f"Ticker {ticker} not found in fetched multi-index columns: {ke}. Skipping {ticker}.")
                except Exception as e:
                    logger.error(f"Error processing multi-index data for {ticker}: {e}")

            if is_single_symbol:
                return all_data_dict.get(symbols_list[0], pd.DataFrame()) # 단일 심볼 요청 시 해당 DataFrame 반환
            else:
                return all_data_dict # 여러 심볼 요청 시 딕셔너리 반환

        else: # 단일 심볼 요청 시 멀티인덱스가 아닌 일반 DataFrame이 반환될 경우
            # 컬럼명 통일 (첫 글자 대문자)
            # 문자열 형태의 튜플 컬럼 처리 로직도 여기에 포함
            new_columns = []
            for col in df_raw.columns:
                if isinstance(col, str) and col.startswith("('") and col.endswith("')"):
                    try:
                        evaluated_col = ast.literal_eval(col)
                        if isinstance(evaluated_col, tuple) and len(evaluated_col) > 0:
                            new_columns.append(str(evaluated_col[0]).capitalize())
                        else:
                            new_columns.append(str(col).capitalize())
                    except (ValueError, SyntaxError):
                        new_columns.append(str(col).capitalize())
                else:
                    new_columns.append(str(col).capitalize())
            df_raw.columns = new_columns

            # DatetimeIndex 확인 및 정렬
            if not isinstance(df_raw.index, pd.DatetimeIndex):
                df_raw.index = pd.to_datetime(df_raw.index)
            df_raw.sort_index(inplace=True)

            # 필요한 컬럼만 유지
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                if col not in df_raw.columns:
                    logger.error(f"Missing required column '{col}' for {symbols_list[0]} from Yahoo Finance data. Available columns: {df_raw.columns.tolist()}")
                    return pd.DataFrame()
            df_raw = df_raw[required_cols]

            logger.info(f"Successfully fetched {len(df_raw)} rows of {interval} data for {symbols_list[0]}.")
            return df_raw # 단일 심볼 요청 시 DataFrame 반환

    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching data for {symbols_list}: {e}")
        return pd.DataFrame() if is_single_symbol else {}
