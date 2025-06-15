# stock_bot/database/manager.py
# 역할: 모든 데이터베이스 CRUD(생성, 읽기, 수정, 삭제) 로직을 메서드로 제공하는 클래스.
# 기존 database_manager.py의 모든 기능을 포함합니다.

import logging
import pandas as pd
import uuid
import json
from sqlalchemy.dialects.mysql import insert as mysql_insert
from datetime import datetime, timedelta, timezone

# 같은 패키지 내의 connection 모듈과 models 모듈을 참조합니다.
from .connection import get_db_session
from .models import (StockMetadata, TradingSignal, IntradayOhlcv,
                     TechnicalIndicator, DailyPrediction)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    데이터베이스와의 모든 상호작용을 관리하는 클래스입니다.
    기존 database_manager.py의 함수들을 클래스 메소드로 변환했습니다.
    """

    def get_stocks_to_analyze(self) -> list[str]:
        """분석이 필요한(need_analysis=True) 주식 티커 목록을 DB에서 가져옵니다."""
        with get_db_session() as db:
            try:
                stocks = db.query(StockMetadata.ticker).filter(
                    StockMetadata.need_analysis == True,
                    StockMetadata.is_active == True
                ).all()
                return [stock[0] for stock in stocks]
            except Exception as e:
                logger.error(f"Error fetching stocks to analyze: {e}")
                return []

    def save_intraday_ohlcv(self, df_ohlcv: pd.DataFrame, ticker: str, interval: str = '1m'):
        """OHLCV 데이터를 DB에 저장(Upsert)합니다."""
        if df_ohlcv.empty:
            return

        with get_db_session() as db:
            try:
                df_to_save = df_ohlcv.copy()
                df_to_save.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                if df_to_save.empty:
                    return

                if not isinstance(df_to_save.index, pd.DatetimeIndex):
                    return
                df_to_save['timestamp_utc'] = pd.to_datetime(df_to_save.index).tz_localize(None) # TZ 정보 제거
                df_to_save['ticker'] = ticker
                df_to_save['interval'] = interval

                df_to_save = df_to_save[['timestamp_utc', 'ticker', 'interval', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df_to_save.columns = ['timestamp_utc', 'ticker', 'interval', 'open', 'high', 'low', 'close', 'volume']
                df_to_save['volume'] = df_to_save['volume'].fillna(0).astype('int64')

                records_to_upsert = df_to_save.to_dict(orient='records')
                if not records_to_upsert:
                    return

                stmt = mysql_insert(IntradayOhlcv).values(records_to_upsert)
                on_duplicate_key_stmt = stmt.on_duplicate_key_update(
                    open=stmt.inserted.open, high=stmt.inserted.high,
                    low=stmt.inserted.low, close=stmt.inserted.close,
                    volume=stmt.inserted.volume, interval=stmt.inserted.interval
                )
                db.execute(on_duplicate_key_stmt)
                db.commit()
            except Exception as e:
                logger.error(f"Error upserting OHLCV for {ticker}: {e}", exc_info=True)


    def get_intraday_ohlcv_for_analysis(self, ticker: str, lookback_days: int) -> pd.DataFrame:
        """분석에 필요한 기간만큼의 1분봉 OHLCV 데이터를 DB에서 조회합니다."""
        with get_db_session() as db:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
                query = db.query(IntradayOhlcv).filter(
                    IntradayOhlcv.ticker == ticker,
                    IntradayOhlcv.timestamp_utc >= start_date
                ).order_by(IntradayOhlcv.timestamp_utc)

                df = pd.read_sql(query.statement, db.bind)
                if df.empty:
                    return pd.DataFrame()

                df.set_index(pd.to_datetime(df['timestamp_utc']), inplace=True)
                df.drop(columns=['timestamp_utc'], inplace=True)
                df.columns = [col.capitalize() for col in df.columns]
                return df
            except Exception as e:
                logger.error(f"Error fetching OHLCV from DB for {ticker}: {e}")
                return pd.DataFrame()

    def get_bulk_resampled_ohlcv_from_db(self, tickers: list[str], start_date: datetime, end_date: datetime, freq: str) -> dict[str, pd.DataFrame]:
        """DB의 1분봉 데이터를 리샘플링하여 지정된 주기의 OHLCV 데이터를 생성합니다."""
        with get_db_session() as db:
            results_dict = {}
            try:
                query = db.query(IntradayOhlcv).filter(
                    IntradayOhlcv.ticker.in_(tickers),
                    IntradayOhlcv.timestamp_utc.between(start_date, end_date)
                )
                df_all = pd.read_sql(query.statement, db.bind)
                if df_all.empty:
                    return {}

                df_all['timestamp_utc'] = pd.to_datetime(df_all['timestamp_utc'])
                df_all.set_index('timestamp_utc', inplace=True)

                rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
                df_resampled_all = df_all.groupby('ticker').resample(freq).apply(rules)
                df_resampled_all.dropna(inplace=True)

                for ticker in tickers:
                    if ticker in df_resampled_all.index.get_level_values('ticker'):
                        df_ticker = df_resampled_all.loc[ticker].copy()
                        df_ticker.columns = [col.capitalize() for col in df_ticker.columns]
                        results_dict[ticker] = df_ticker
                return results_dict
            except Exception as e:
                logger.error(f"Error during bulk resampling: {e}", exc_info=True)
                return {}

    def save_technical_indicators(self, df_indicators: pd.DataFrame, ticker: str, interval: str):
        """계산된 기술적 지표를 DB에 저장(Upsert)합니다."""
        if df_indicators.empty:
            return

        with get_db_session() as db:
            try:
                df_to_save = df_indicators.copy()
                if 'Ticker' in df_to_save.columns:
                    df_to_save = df_to_save.drop(columns=['Ticker'])

                if not isinstance(df_to_save.index, pd.DatetimeIndex):
                    return
                df_to_save['timestamp_utc'] = pd.to_datetime(df_to_save.index).tz_localize(None)
                df_to_save['ticker'] = ticker
                df_to_save['data_interval'] = interval
                df_to_save.columns = df_to_save.columns.str.lower().str.replace('.', '_', regex=False)

                model_columns = set(TechnicalIndicator.__table__.columns.keys())
                cols_to_keep = [col for col in df_to_save.columns if col in model_columns]
                df_to_save = df_to_save[cols_to_keep]
                df_to_save = df_to_save.astype(object).where(pd.notnull(df_to_save), None)

                records_to_upsert = df_to_save.to_dict(orient='records')
                if not records_to_upsert:
                    return

                stmt = mysql_insert(TechnicalIndicator).values(records_to_upsert)
                update_dict = {col.name: col for col in stmt.inserted if not col.primary_key}
                on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
                db.execute(on_duplicate_key_stmt)
                db.commit()
            except Exception as e:
                logger.error(f"Error upserting indicators for {ticker}: {e}", exc_info=True)


    def save_trading_signal(self, signal_data: dict):
        """거래 신호 데이터를 저장합니다."""
        with get_db_session() as db:
            try:
                new_signal = TradingSignal(
                    signal_id=str(uuid.uuid4()),
                    timestamp_utc=signal_data.get('timestamp'),
                    ticker=signal_data.get('ticker'),
                    signal_type=signal_data.get('type'),
                    signal_score=signal_data.get('score'),
                    market_trend=signal_data.get('market_trend'),
                    long_term_trend=signal_data.get('long_term_trend'),
                    trend_ref_close=signal_data.get('trend_ref_close'),
                    trend_ref_value=signal_data.get('trend_ref_value'),
                    details=json.dumps(signal_data.get('details', [])),
                    price_at_signal=signal_data.get('current_price'),
                    stop_loss_price=signal_data.get('stop_loss_price')
                )
                db.add(new_signal)
                db.commit()
                logger.info(f"Successfully saved signal for {new_signal.ticker}.")
            except Exception as e:
                logger.error(f"Error saving trading signal: {e}")


    def save_daily_prediction(self, prediction_data: dict):
        """일일 예측 데이터를 저장합니다."""
        with get_db_session() as db:
            try:
                new_prediction = DailyPrediction(
                    prediction_id=str(uuid.uuid4()),
                    prediction_date_utc=prediction_data.get('prediction_date_utc'),
                    generated_at_utc=prediction_data.get('generated_at_utc'),
                    ticker=prediction_data.get('ticker'),
                    predicted_price_type=prediction_data.get('price_type'),
                    predicted_price=prediction_data.get('price'),
                    predicted_range_low=prediction_data.get('range_low'),
                    predicted_range_high=prediction_data.get('range_high'),
                    reason=prediction_data.get('reason'),
                    prediction_score=prediction_data.get('score'),
                    details=json.dumps(prediction_data.get('details', [])),
                    prev_day_close=prediction_data.get('prev_day_close')
                )
                db.add(new_prediction)
                db.commit()
                logger.info(f"Successfully saved prediction for {new_prediction.ticker}.")
            except Exception as e:
                logger.error(f"Error saving daily prediction: {e}")

    def update_stock_metadata(self, metadata_list: list[dict]):
        """주식 메타데이터를 업데이트하거나 삽입(Upsert)합니다."""
        with get_db_session() as db:
            try:
                tickers_in_batch = {meta.get('ticker') for meta in metadata_list if meta.get('ticker')}
                existing_stocks = db.query(StockMetadata).filter(StockMetadata.ticker.in_(tickers_in_batch)).all()
                existing_tickers_map = {stock.ticker: stock for stock in existing_stocks}

                for meta in metadata_list:
                    ticker = meta.get('ticker')
                    if not ticker:
                        continue

                    if ticker in existing_tickers_map:
                        existing_stock = existing_tickers_map[ticker]
                        for key, value in meta.items():
                            setattr(existing_stock, key, value)
                    else:
                        meta['need_analysis'] = True
                        db.add(StockMetadata(**meta))

                db.commit()
                logger.info(f"Successfully updated/inserted {len(metadata_list)} metadata records.")
            except Exception as e:
                logger.error(f"Error updating stock metadata: {e}")

