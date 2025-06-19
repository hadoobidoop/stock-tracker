from typing import List, Optional
import pandas as pd
from datetime import datetime
import numpy as np
from sqlalchemy.dialects.mysql import insert as mysql_insert

from infrastructure.logging import get_logger
from infrastructure.db import get_db
from infrastructure.db.models.technical_indicator import TechnicalIndicator as TechnicalIndicatorModel
from domain.analysis.repository.technical_indicator_repository import TechnicalIndicatorRepository
from domain.analysis.models.technical_indicator import TechnicalIndicator

logger = get_logger(__name__)


class SQLTechnicalIndicatorRepository(TechnicalIndicatorRepository):
    """SQLAlchemy를 사용한 기술적 지표 저장소 구현체"""
    
    def save_indicators(self, indicators_df: pd.DataFrame, ticker: str, interval: str) -> bool:
        """
        기술적 지표를 데이터베이스에 한 번에 저장하거나 업데이트합니다 (UPSERT).
        pandas.DataFrame의 NaN 값을 None으로 변환하여 DB에 저장할 수 있도록 합니다.
        """
        if indicators_df.empty:
            return True

        try:
            with get_db() as db:
                # 1. 테이블 컬럼 정보 가져오기
                table = TechnicalIndicatorModel.__table__
                valid_columns = {c.name for c in table.columns}
                
                # 2. NaN을 None으로 변환
                df_clean = indicators_df.replace({np.nan: None})
                
                # 3. DataFrame을 딕셔너리 리스트로 변환하고 컬럼명을 소문자로 변환
                records_to_save = []
                for timestamp, row in df_clean.iterrows():
                    record = {}
                    for col, val in row.items():
                        # 컬럼명을 소문자로 변환
                        db_col = col.lower()
                        # ATR_14 -> atrr_14 특수 케이스 처리
                        if db_col == 'atr_14':
                            db_col = 'atrr_14'
                        # 데이터베이스에 존재하는 컬럼만 포함
                        if db_col in valid_columns:
                            record[db_col] = val
                    
                    record['timestamp_utc'] = timestamp
                    record['ticker'] = ticker
                    record['data_interval'] = interval
                    records_to_save.append(record)

                if not records_to_save:
                    return True

                # 4. 실제 데이터에 존재하는 컬럼만 필터링
                actual_columns = set(records_to_save[0].keys())
                valid_update_columns = actual_columns & valid_columns - {'id', 'ticker', 'timestamp_utc', 'created_at'}

                # 5. SQLAlchemy 2.0 스타일의 ORM 기반 Upsert
                stmt = mysql_insert(TechnicalIndicatorModel).values(records_to_save)
                
                # 업데이트할 값들을 명시 (실제 존재하는 컬럼만)
                update_dict = {
                    col: stmt.inserted[col] 
                    for col in valid_update_columns
                }
                
                on_duplicate_key_stmt = stmt.on_duplicate_key_update(**update_dict)
                
                db.execute(on_duplicate_key_stmt)
                db.commit()
                
                logger.info(f"Successfully saved/updated {len(records_to_save)} technical indicators for {ticker}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving technical indicators for {ticker}: {e}", exc_info=True)
            return False
    
    def get_indicators(self, ticker: str, interval: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """특정 기간의 기술적 지표를 조회합니다."""
        try:
            with get_db() as db:
                indicators = db.query(TechnicalIndicatorModel).filter(
                    TechnicalIndicatorModel.ticker == ticker,
                    TechnicalIndicatorModel.data_interval == interval,
                    TechnicalIndicatorModel.timestamp_utc >= start_time,
                    TechnicalIndicatorModel.timestamp_utc <= end_time
                ).order_by(TechnicalIndicatorModel.timestamp_utc).all()
                
                if not indicators:
                    return pd.DataFrame()
                
                # DataFrame으로 변환
                data = []
                for indicator in indicators:
                    data.append({
                        'timestamp_utc': indicator.timestamp_utc,
                        'ticker': indicator.ticker,
                        'data_interval': indicator.data_interval,
                        'SMA_5': indicator.sma_5,
                        'SMA_20': indicator.sma_20,
                        'SMA_60': indicator.sma_60,
                        'RSI_14': indicator.rsi_14,
                        'MACD_12_26_9': indicator.macd_12_26_9,
                        'MACDs_12_26_9': indicator.macds_12_26_9,
                        'MACDh_12_26_9': indicator.macdh_12_26_9,
                        'STOCHk_14_3_3': indicator.stochk_14_3_3,
                        'STOCHd_14_3_3': indicator.stochd_14_3_3,
                        'ADX_14': indicator.adx_14,
                        'DMP_14': indicator.dmp_14,
                        'DMN_14': indicator.dmn_14,
                        'BBL_20_2_0': indicator.bbl_20_2_0,
                        'BBM_20_2_0': indicator.bbm_20_2_0,
                        'BBU_20_2_0': indicator.bbu_20_2_0,
                        'ATR_14': indicator.atrr_14,
                        'Volume_SMA_20': indicator.volume_sma_20,
                    })
                
                df = pd.DataFrame(data)
                df.set_index('timestamp_utc', inplace=True)
                return df
                
        except Exception as e:
            logger.error(f"Error getting indicators for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_latest_indicators(self, ticker: str, interval: str, limit: int = 1) -> pd.DataFrame:
        """최신 기술적 지표를 조회합니다."""
        try:
            with get_db() as db:
                indicators = db.query(TechnicalIndicatorModel).filter(
                    TechnicalIndicatorModel.ticker == ticker,
                    TechnicalIndicatorModel.data_interval == interval
                ).order_by(TechnicalIndicatorModel.timestamp_utc.desc()).limit(limit).all()
                
                if not indicators:
                    return pd.DataFrame()
                
                # DataFrame으로 변환 (위와 동일한 로직)
                data = []
                for indicator in indicators:
                    data.append({
                        'timestamp_utc': indicator.timestamp_utc,
                        'ticker': indicator.ticker,
                        'data_interval': indicator.data_interval,
                        'SMA_5': indicator.sma_5,
                        'SMA_20': indicator.sma_20,
                        'SMA_60': indicator.sma_60,
                        'RSI_14': indicator.rsi_14,
                        'MACD_12_26_9': indicator.macd_12_26_9,
                        'MACDs_12_26_9': indicator.macds_12_26_9,
                        'MACDh_12_26_9': indicator.macdh_12_26_9,
                        'STOCHk_14_3_3': indicator.stochk_14_3_3,
                        'STOCHd_14_3_3': indicator.stochd_14_3_3,
                        'ADX_14': indicator.adx_14,
                        'DMP_14': indicator.dmp_14,
                        'DMN_14': indicator.dmn_14,
                        'BBL_20_2_0': indicator.bbl_20_2_0,
                        'BBM_20_2_0': indicator.bbm_20_2_0,
                        'BBU_20_2_0': indicator.bbu_20_2_0,
                        'ATR_14': indicator.atrr_14,
                        'Volume_SMA_20': indicator.volume_sma_20,
                    })
                
                df = pd.DataFrame(data)
                df.set_index('timestamp_utc', inplace=True)
                return df
                
        except Exception as e:
            logger.error(f"Error getting latest indicators for {ticker}: {e}")
            return pd.DataFrame()
    
    def delete_old_indicators(self, ticker: str, interval: str, before_time: datetime) -> int:
        """오래된 기술적 지표를 삭제합니다."""
        try:
            with get_db() as db:
                deleted_count = db.query(TechnicalIndicatorModel).filter(
                    TechnicalIndicatorModel.ticker == ticker,
                    TechnicalIndicatorModel.data_interval == interval,
                    TechnicalIndicatorModel.timestamp_utc < before_time
                ).delete()
                
                db.commit()
                logger.info(f"Deleted {deleted_count} old indicators for {ticker}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error deleting old indicators for {ticker}: {e}")
            return 0
    
    def _update_existing_indicator(self, existing: TechnicalIndicatorModel, row: pd.Series, interval: str):
        """기존 지표를 업데이트합니다."""
        for col_name, value in row.items():
            if hasattr(existing, col_name.lower()):
                setattr(existing, col_name.lower(), value if not pd.isna(value) else None)
        existing.data_interval = interval
    
    def _create_new_indicator(self, row: pd.Series, ticker: str, interval: str) -> TechnicalIndicatorModel:
        """새로운 지표를 생성합니다."""
        indicator_data = {
            'timestamp_utc': row.name,
            'ticker': ticker,
            'data_interval': interval,
        }
        for col_name, value in row.items():
            indicator_data[col_name.lower()] = value if not pd.isna(value) else None
        
        # 모델에 없는 필터링 (예: 'Volume')
        valid_cols = {c.name for c in TechnicalIndicatorModel.__table__.columns}
        filtered_data = {k: v for k, v in indicator_data.items() if k in valid_cols}
        
        return TechnicalIndicatorModel(**filtered_data) 