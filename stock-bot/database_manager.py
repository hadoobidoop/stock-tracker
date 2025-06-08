
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
        stocks = db.query(StockMetadata.ticker).filter(StockMetadata.need_analysis == True, StockMetadata.is_active == True).all()
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

        details=json.dumps(signal_data.get('details', [])) if isinstance(signal_data.get('details'), list) else signal_data.get('details'),
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
        details=json.dumps(prediction_data.get('details', [])) if isinstance(prediction_data.get('details'), list) else prediction_data.get('details'),
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
    [수정됨] 주식 메타데이터를 업데이트합니다.
    새로 추가되는 종목에만 need_analysis=True를 설정하고, 기존 종목의 플래그는 건드리지 않습니다.
    """

    db: Session = next(get_db())
    try:
        for meta in metadata_list:
            ticker = meta.get('ticker')
            if not ticker:
                continue

            # DB에 해당 티커가 이미 있는지 확인
            existing_stock = db.query(StockMetadata).filter(StockMetadata.ticker == ticker).first()

            # 없는 경우에만, need_analysis를 True로 설정
            if not existing_stock:
                meta['need_analysis'] = True

            # merge를 사용하여 데이터가 있으면 업데이트, 없으면 삽입
            db.merge(StockMetadata(**meta))
        db.commit()
        logger.info(f"Successfully updated {len(metadata_list)} metadata records.")
    except Exception as e:
        logger.error(f"Error updating stock metadata: {e}")
        db.rollback()
    finally:
        db.close()
