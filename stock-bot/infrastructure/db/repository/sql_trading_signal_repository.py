from typing import List, Optional
from datetime import datetime

from infrastructure.logging import get_logger
from infrastructure.db import get_db
from infrastructure.db.models.trading_signal import TradingSignal as TradingSignalModel
from domain.analysis.repository.trading_signal_repository import TradingSignalRepository
from domain.analysis.models.trading_signal import TradingSignal

logger = get_logger(__name__)


class SQLTradingSignalRepository(TradingSignalRepository):
    """SQLAlchemy를 사용한 거래 신호 저장소 구현체"""
    
    def save_signal(self, signal: TradingSignal) -> bool:
        """거래 신호를 저장합니다."""
        try:
            with get_db() as db:
                signal_model = TradingSignalModel(
                    ticker=signal.ticker,
                    signal_type=signal.signal_type,
                    signal_score=signal.signal_score,
                    timestamp_utc=signal.timestamp_utc,
                    current_price=signal.current_price,
                    market_trend=signal.market_trend,
                    long_term_trend=signal.long_term_trend,
                    trend_ref_close=signal.trend_ref_close,
                    trend_ref_value=signal.trend_ref_value,
                    details=signal.details,
                    stop_loss_price=signal.stop_loss_price
                )
                
                db.add(signal_model)
                db.commit()
                
                logger.info(f"Saved trading signal for {signal.ticker}: {signal.signal_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving trading signal: {e}")
            return False
    
    def save_signals_bulk(self, signals: List[TradingSignal]) -> bool:
        """여러 거래 신호를 한 번에 저장합니다."""
        try:
            with get_db() as db:
                signal_models = []
                for signal in signals:
                    signal_model = TradingSignalModel(
                        ticker=signal.ticker,
                        signal_type=signal.signal_type,
                        signal_score=signal.signal_score,
                        timestamp_utc=signal.timestamp_utc,
                        current_price=signal.current_price,
                        market_trend=signal.market_trend,
                        long_term_trend=signal.long_term_trend,
                        trend_ref_close=signal.trend_ref_close,
                        trend_ref_value=signal.trend_ref_value,
                        details=signal.details,
                        stop_loss_price=signal.stop_loss_price
                    )
                    signal_models.append(signal_model)
                
                db.add_all(signal_models)
                db.commit()
                
                logger.info(f"Saved {len(signals)} trading signals")
                return True
                
        except Exception as e:
            logger.error(f"Error saving trading signals bulk: {e}")
            return False
    
    def get_signals_by_ticker(self, ticker: str, start_time: datetime, end_time: datetime) -> List[TradingSignal]:
        """특정 종목의 거래 신호를 조회합니다."""
        try:
            with get_db() as db:
                signals = db.query(TradingSignalModel).filter(
                    TradingSignalModel.ticker == ticker,
                    TradingSignalModel.timestamp_utc >= start_time,
                    TradingSignalModel.timestamp_utc <= end_time
                ).order_by(TradingSignalModel.timestamp_utc.desc()).all()
                
                return [self._convert_to_domain(signal) for signal in signals]
                
        except Exception as e:
            logger.error(f"Error getting signals by ticker: {e}")
            return []
    
    def get_latest_signals(self, ticker: str, limit: int = 10) -> List[TradingSignal]:
        """최신 거래 신호를 조회합니다."""
        try:
            with get_db() as db:
                signals = db.query(TradingSignalModel).filter(
                    TradingSignalModel.ticker == ticker
                ).order_by(TradingSignalModel.timestamp_utc.desc()).limit(limit).all()
                
                return [self._convert_to_domain(signal) for signal in signals]
                
        except Exception as e:
            logger.error(f"Error getting latest signals: {e}")
            return []
    
    def get_signals_by_type(self, signal_type: str, start_time: datetime, end_time: datetime) -> List[TradingSignal]:
        """특정 타입의 거래 신호를 조회합니다."""
        try:
            with get_db() as db:
                signals = db.query(TradingSignalModel).filter(
                    TradingSignalModel.signal_type == signal_type,
                    TradingSignalModel.timestamp_utc >= start_time,
                    TradingSignalModel.timestamp_utc <= end_time
                ).order_by(TradingSignalModel.timestamp_utc.desc()).all()
                
                return [self._convert_to_domain(signal) for signal in signals]
                
        except Exception as e:
            logger.error(f"Error getting signals by type: {e}")
            return []
    
    def delete_old_signals(self, before_time: datetime) -> int:
        """오래된 거래 신호를 삭제합니다."""
        try:
            with get_db() as db:
                deleted_count = db.query(TradingSignalModel).filter(
                    TradingSignalModel.timestamp_utc < before_time
                ).delete()
                
                db.commit()
                logger.info(f"Deleted {deleted_count} old trading signals")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error deleting old signals: {e}")
            return 0
    
    def _convert_to_domain(self, db_signal: TradingSignalModel) -> TradingSignal:
        """DB 모델을 도메인 모델로 변환합니다."""
        return TradingSignal(
            ticker=db_signal.ticker,
            signal_type=db_signal.signal_type,
            signal_score=db_signal.signal_score,
            timestamp_utc=db_signal.timestamp_utc,
            current_price=db_signal.current_price,
            market_trend=db_signal.market_trend,
            long_term_trend=db_signal.long_term_trend,
            trend_ref_close=db_signal.trend_ref_close,
            trend_ref_value=db_signal.trend_ref_value,
            details=db_signal.details,
            stop_loss_price=db_signal.stop_loss_price
        ) 