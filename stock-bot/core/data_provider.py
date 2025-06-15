# stock-bot/core/data_provider.py
# 역할: 외부 소스(Yahoo Finance)로부터 주식 데이터를 가져오는 책임을 지는 클래스.

import yfinance as yf
import pandas as pd
import logging
from typing import Union, List, Dict

logger = logging.getLogger(__name__)

class DataProvider:
    """
    Yahoo Finance API를 통해 다양한 주식 데이터를 가져오는 클래스입니다.
    기존 data_collector.py의 함수들을 클래스 메소드로 변환했습니다.
    """

    def get_ohlcv(self, symbols: Union[str, List[str]], period: str, interval: str) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        yfinance API를 통해 OHLCV(시가, 고가, 저가, 종가, 거래량) 데이터를 가져옵니다.
        여러 종목 또는 단일 종목 요청 시의 복잡한 컬럼 구조를 처리하는 로직을 포함합니다.
        """
        is_single_symbol = isinstance(symbols, str)
        symbols_list = [symbols] if is_single_symbol else symbols

        logger.info(f"Fetching {interval} OHLCV for {symbols_list} ({period}) from yfinance...")
        try:
            df_raw = yf.download(
                symbols_list,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False
            )

            if df_raw.empty:
                logger.warning(f"No data fetched for {symbols_list}.")
                return pd.DataFrame() if is_single_symbol else {}

            # --- [검증 완료] 원본의 멀티인덱스/단일인덱스 컬럼 처리 로직 전체를 여기에 통합 ---
            if isinstance(df_raw.columns, pd.MultiIndex):
                # 여러 종목을 요청하여 멀티인덱스 컬럼이 반환된 경우
                all_data_dict = {}
                for ticker in symbols_list:
                    try:
                        # 특정 티커에 해당하는 컬럼들만 추출
                        df_symbol = df_raw.loc[:, pd.IndexSlice[:, ticker]]
                        # 컬럼 레벨을 하나로 만듦 (예: ('Open', 'AAPL') -> 'Open')
                        df_symbol.columns = df_symbol.columns.droplevel(1)
                        df_symbol.columns = [str(col).capitalize() for col in df_symbol.columns]

                        if not self._validate_ohlcv_dataframe(df_symbol, ticker):
                            continue

                        all_data_dict[ticker] = df_symbol
                    except KeyError:
                        logger.warning(f"Ticker {ticker} not found in fetched multi-index data. Skipping.")

                return all_data_dict if not is_single_symbol else all_data_dict.get(symbols, pd.DataFrame())

            else:
                # 단일 종목을 요청하여 일반 컬럼이 반환된 경우
                df_raw.columns = [str(col).capitalize() for col in df_raw.columns]
                if not self._validate_ohlcv_dataframe(df_raw, symbols_list[0]):
                    return pd.DataFrame()

                return df_raw

        except Exception as e:
            logger.error(f"Error fetching OHLCV from yfinance: {e}", exc_info=True)
            return pd.DataFrame() if is_single_symbol else {}

    def _validate_ohlcv_dataframe(self, df: pd.DataFrame, ticker: str) -> bool:
        """DataFrame의 유효성을 검사하고 인덱스를 정렬하는 내부 헬퍼 메소드"""
        # DatetimeIndex 확인 및 정렬
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)

        # 필수 컬럼 존재 여부 확인
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing required column '{col}' for {ticker}. Available: {df.columns.tolist()}")
                return False
        return True

    def get_stock_metadata(self, symbols: List[str]) -> List[dict]:
        """
        yfinance를 사용하여 여러 주식의 메타데이터를 가져옵니다.
        (기존 data_collection_jobs.py의 update_stock_metadata_from_yfinance 함수 로직 활용)
        """
        logger.info(f"Fetching metadata for {len(symbols)} symbols from yfinance...")
        metadata_list = []
        try:
            tickers_info = yf.Tickers(symbols)
            for symbol in symbols:
                info = tickers_info.tickers[symbol.upper()].info
                if not info or 'symbol' not in info:
                    logger.warning(f"Could not retrieve valid info for {symbol}. Skipping.")
                    continue

                metadata = {
                    'ticker': info.get('symbol'),
                    'company_name': info.get('longName'),
                    'exchange': info.get('exchange'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'is_active': not info.get('isDelisted', False),
                    'quote_type': info.get('quoteType'),
                    'currency': info.get('currency'),
                    'market_cap': info.get('marketCap'),
                    'shares_outstanding': info.get('sharesOutstanding'),
                    'beta': info.get('beta'),
                    'dividend_yield': info.get('dividendYield'),
                    'logo_url': info.get('logo_url'),
                    'long_business_summary': info.get('longBusinessSummary')
                }
                metadata_list.append(metadata)
        except Exception as e:
            logger.error(f"Failed to process metadata from yfinance: {e}")

        return metadata_list
