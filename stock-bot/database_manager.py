import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.dialects.mysql import insert as mysql_insert
import pandas as pd
from sqlalchemy.orm import Session
from database_setup import SessionLocal, TechnicalIndicator, TradingSignal, DailyPrediction, StockMetadata, \
    IntradayOhlcv
import logging
import json

logger = logging.getLogger(__name__)


def save_intraday_ohlcv(df_ohlcv: pd.DataFrame, ticker: str):
    """(최종 오류 수정) NaN 데이터를 완벽하게 정제한 후, 안정적으로 DB에 저장합니다."""
    if df_ohlcv.empty:
        return

    db: Session = next(get_db())
    try:
        df_to_save = df_ohlcv.copy()

        # --- [수정된 부분 시작] ---
        # 1. 가격 정보(OHLC)가 하나라도 없는 행(row)은 분석 가치가 없으므로 먼저 삭제합니다.
        #    이것이 'Unknown column 'nan'' 오류의 근본적인 해결책입니다.
        df_to_save.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)

        # 만약 모든 행이 유효하지 않아 삭제되었다면, 더 이상 진행하지 않습니다.
        if df_to_save.empty:
            logger.warning(f"No valid OHLC data rows found for {ticker} after cleaning. Skipping save.")
            return

        # 2. 벡터화(Vectorization)를 사용하여 안정적이고 빠르게 데이터를 준비합니다.
        if not isinstance(df_to_save.index, pd.DatetimeIndex):
            logger.error(f"DataFrame for {ticker} does not have a DatetimeIndex. Skipping save.")
            return
        df_to_save['timestamp_utc'] =  pd.to_datetime(df_to_save.index).to_pydatetime()
        df_to_save['ticker'] = ticker

        df_to_save = df_to_save[['timestamp_utc', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df_to_save.columns = ['timestamp_utc', 'ticker', 'open', 'high', 'low', 'close', 'volume']

        # 3. Volume 컬럼에 남아있을 수 있는 NaN 값을 0으로 채우고 정수형으로 변환합니다.
        df_to_save['volume'] = df_to_save['volume'].fillna(0).astype('int64')
        # --- [수정된 부분 끝] ---

        records_to_upsert = df_to_save.to_dict(orient='records')

        if not records_to_upsert: return

        stmt = mysql_insert(IntradayOhlcv).values(records_to_upsert)
        on_duplicate_key_stmt = stmt.on_duplicate_key_update(
            open=stmt.inserted.open, high=stmt.inserted.high,
            low=stmt.inserted.low, close=stmt.inserted.close,
            volume=stmt.inserted.volume,
        )

        db.execute(on_duplicate_key_stmt)
        db.commit()
        logger.debug(f"Successfully upserted {len(records_to_upsert)} OHLCV records for {ticker}.")

    except Exception as e:
        logger.error(f"Error upserting OHLCV data for {ticker}: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

def get_intraday_ohlcv_for_analysis(ticker: str, lookback_days: int) -> pd.DataFrame:
    """분석에 필요한 기간만큼의 1분봉 OHLCV 데이터를 내부 DB에서 조회합니다."""
    db: Session = next(get_db())
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        query = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.ticker == ticker, IntradayOhlcv.timestamp_utc >= start_date
        ).order_by(IntradayOhlcv.timestamp_utc)
        df = pd.read_sql(query.statement, db.bind)
        if df.empty: return pd.DataFrame()
        df.set_index(pd.to_datetime(df['timestamp_utc']), inplace=True)
        df.drop(columns=['timestamp_utc'], inplace=True)
        # 컬럼명을 yfinance와 동일한 형식(첫글자 대문자)으로 변경하여 후속 계산에 사용
        df.columns = [col.capitalize() for col in df.columns]
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV from DB for {ticker}: {e}")
        return pd.DataFrame()
    finally:
        db.close()


def get_bulk_resampled_ohlcv_from_db(tickers: list[str], start_date: datetime, end_date: datetime, freq: str) -> dict[str, pd.DataFrame]:
    """
    (타입 힌트 오류 수정) DB에 저장된 1분봉 데이터를 기반으로, 지정된 주기의 OHLCV 데이터를 생성(리샘플링)합니다.
    모든 코드 경로에서 항상 dict를 반환하도록 수정되었습니다.
    """
    db: Session = next(get_db())
    results_dict = {}
    try:
        logger.info(f"Bulk resampling data for {len(tickers)} tickers with frequency '{freq}'...")
        query = db.query(IntradayOhlcv).filter(
            IntradayOhlcv.ticker.in_(tickers), IntradayOhlcv.timestamp_utc.between(start_date, end_date)
        )
        df_all = pd.read_sql(query.statement, db.bind)
        if df_all.empty:
            logger.warning("No data found in DB for bulk resampling.")
            return {}

        df_all['timestamp_utc'] = pd.to_datetime(df_all['timestamp_utc'])
        df_all.set_index('timestamp_utc', inplace=True)
        resampling_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_resampled_all = df_all.groupby('ticker').resample(freq).apply(resampling_rules)
        df_resampled_all.dropna(inplace=True)

        for ticker in tickers:
            if ticker in df_resampled_all.index.get_level_values('ticker'):
                df_ticker = df_resampled_all.loc[ticker].copy()
                df_ticker.columns = [col.capitalize() for col in df_ticker.columns]
                results_dict[ticker] = df_ticker

        logger.info(f"Successfully resampled data for {len(results_dict)} tickers.")
        return results_dict

    except Exception as e:
        logger.error(f"Error during bulk resampling: {e}", exc_info=True)
        return {}
    finally:
        db.close()

def save_technical_indicators(df_indicators: pd.DataFrame, ticker: str, interval: str):
    """(최종 검증) 벡터화를 사용하여 계산된 기술적 지표를 안정적이고 빠르게 저장합니다."""
    if df_indicators.empty: return
    db: Session = next(get_db())

    try:
        df_to_save = df_indicators.copy()
        # --- [수정 코드 추가] ---
        # 기존에 있을 수 있는 Ticker 컬럼을 삭제하여 중복 방지
        if 'Ticker' in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=['Ticker'])
        # --- [수정 코드 끝] ---

        if not isinstance(df_to_save.index, pd.DatetimeIndex):
            logger.error(f"Indicator DataFrame for {ticker} does not have a DatetimeIndex. Skipping save.")
            return
        df_to_save['timestamp_utc'] = pd.to_datetime(df_to_save.index).to_pydatetime()
        df_to_save['ticker'] = ticker
        df_to_save['data_interval'] = interval
        df_to_save.columns = df_to_save.columns.str.lower()
        df_to_save.columns = [col.replace('.', '_') for col in df_to_save.columns]
        model_columns = set(TechnicalIndicator.__table__.columns.keys())
        cols_to_keep = [col for col in df_to_save.columns if col in model_columns]
        df_to_save = df_to_save[cols_to_keep]
        df_to_save = df_to_save.astype(object).where(pd.notnull(df_to_save), None)

        records_to_upsert = df_to_save.to_dict(orient='records')
        if not records_to_upsert: return
        stmt = mysql_insert(TechnicalIndicator).values(records_to_upsert)
        update_dict = { col.name: col for col in stmt.inserted if not col.primary_key }
        on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
        db.execute(on_duplicate_key_stmt)
        db.commit()
        logger.debug(f"Successfully upserted {len(records_to_upsert)} technical indicator records for {ticker}.")
    except Exception as e:
        logger.error(f"Error upserting technical indicators for {ticker}: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_stocks_to_analyze() -> list[str]:
    """[신규] 분석이 필요한(need_analysis=True) 주식 티커 목록을 DB에서 가져옵니다."""
    db: Session = next(get_db())
    try:
        # StockMetadata 테이블에서 need_analysis가 True인 티커만 조회
        stocks = db.query(StockMetadata.ticker).filter(StockMetadata.need_analysis == True,
                                                       StockMetadata.is_active == True).all()
        # 결과는 [(ticker1,), (ticker2,)] 형태이므로, 각 튜플의 첫 번째 요소를 추출하여 리스트로 변환
        return [stock[0] for stock in stocks]
    except Exception as e:
        logger.error(f"Error fetching stocks to analyze: {e}")
        return []
    finally:
        db.close()


def save_trading_signal(signal_data: dict):
    db: Session = next(get_db())
    new_signal = TradingSignal(
        signal_id=str(uuid.uuid4()),
        timestamp_utc=signal_data.get('timestamp'),
        ticker=signal_data.get('ticker'),
        signal_type=signal_data.get('type'),
        signal_score=signal_data.get('score'),
        market_trend=signal_data.get('market_trend'),
        # --- [신규] 추세 판단 상세 정보 저장 ---
        long_term_trend=signal_data.get('long_term_trend'),
        trend_ref_close=signal_data.get('trend_ref_close'),
        trend_ref_value=signal_data.get('trend_ref_value'),

        details=json.dumps(signal_data.get('details', [])) if isinstance(signal_data.get('details'),
                                                                         list) else signal_data.get('details'),
        price_at_signal=signal_data.get('current_price'),
        stop_loss_price=signal_data.get('stop_loss_price')
    )
    try:
        db.add(new_signal)
        db.commit()
        db.refresh(new_signal)
        logger.info(f"Successfully saved signal {new_signal.signal_id} for {new_signal.ticker}.")
    except Exception as e:
        logger.error(f"Error saving trading signal: {e}")
        db.rollback()
    finally:
        db.close()


def save_daily_prediction(prediction_data: dict):
    db: Session = next(get_db())
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
        details=json.dumps(prediction_data.get('details', [])) if isinstance(prediction_data.get('details'),
                                                                             list) else prediction_data.get('details'),
        prev_day_close=prediction_data.get('prev_day_close')
    )
    try:
        db.add(new_prediction)
        db.commit()
        db.refresh(new_prediction)
        logger.info(f"Successfully saved prediction {new_prediction.prediction_id} for {new_prediction.ticker}.")
    except Exception as e:
        logger.error(f"Error saving daily prediction: {e}")
        db.rollback()
    finally:
        db.close()


def update_stock_metadata(metadata_list: list[dict]):
    """
    [최종 수정본] 주식 메타데이터를 안정적으로 업데이트하거나 삽입합니다 (Upsert).
    Duplicate entry 오류를 근본적으로 해결합니다.
    """
    db: Session = next(get_db())
    try:
        # 처리할 티커 목록을 먼저 추출합니다.
        tickers_in_batch = {meta.get('ticker') for meta in metadata_list if meta.get('ticker')}

        # 1. DB에 해당 티커들이 이미 있는지 한 번의 쿼리로 효율적으로 확인합니다.
        existing_stocks = db.query(StockMetadata).filter(StockMetadata.ticker.in_(tickers_in_batch)).all()
        existing_tickers_map = {stock.ticker: stock for stock in existing_stocks}

        for meta in metadata_list:
            ticker = meta.get('ticker')
            if not ticker:
                continue

            # 2. 메모리에 있는 딕셔너리를 기반으로 업데이트 또는 삽입을 결정합니다.
            if ticker in existing_tickers_map:
                # --- 데이터가 이미 있으면 (UPDATE) ---
                # 받아온 새로운 정보로 기존 객체의 필드를 업데이트합니다.
                existing_stock = existing_tickers_map[ticker]
                for key, value in meta.items():
                    setattr(existing_stock, key, value)
            else:
                # --- 데이터가 없으면 (INSERT) ---
                # 새로운 객체를 만들고, need_analysis 플래그를 True로 설정합니다.
                meta['need_analysis'] = True
                db.add(StockMetadata(**meta))

        # 모든 변경사항을 한번에 커밋합니다.
        db.commit()
        logger.info(f"Successfully updated/inserted {len(metadata_list)} metadata records.")
    except Exception as e:
        logger.error(f"Error updating stock metadata: {e}")
        db.rollback()
    finally:
        db.close()
