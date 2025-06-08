import uuid
import pandas as pd
from sqlalchemy.orm import Session
from database_setup import SessionLocal, TechnicalIndicator, TradingSignal, DailyPrediction, StockMetadata
import logging
import json

logger = logging.getLogger(__name__)


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


def save_technical_indicators(df: pd.DataFrame, ticker: str, interval: str):
    db: Session = next(get_db())
    df.columns = [col.replace('.', '_') for col in df.columns]
    model_columns = set(TechnicalIndicator.__table__.columns.keys())
    records_to_save = []
    for timestamp, row in df.iterrows():
        record_data = row.to_dict()
        filtered_data = {key: record_data.get(key) for key in model_columns if key in record_data}
        if isinstance(timestamp, pd.Timestamp):
            record = TechnicalIndicator(
                timestamp_utc=timestamp.to_pydatetime(),
                ticker=ticker,
                data_interval=interval,
                **filtered_data
            )
            records_to_save.append(record)
    try:
        if records_to_save:
            db.bulk_save_objects(records_to_save)
            db.commit()
            logger.info(f"Successfully saved {len(records_to_save)} indicator records for {ticker}.")
    except Exception as e:
        logger.error(f"Error bulk saving technical indicators for {ticker}: {e}")
        db.rollback()
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
