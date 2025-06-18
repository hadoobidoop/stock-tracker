from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, JSON
from infrastructure.db.db_manager import Base
from infrastructure.db.models.enums import SignalType, TrendType


class TradingSignal(Base):
    """거래 신호 테이블"""
    __tablename__ = 'trading_signals'
    
    signal_id = Column(String(36), primary_key=True)  # UUID는 36자
    timestamp_utc = Column(DateTime, index=True)
    ticker = Column(String(10), index=True)
    signal_type = Column(Enum(SignalType))
    signal_score = Column(Integer)

    market_trend = Column(Enum(TrendType))  # S&P 500 기준 전체 시장 추세
    long_term_trend = Column(Enum(TrendType), nullable=True)
    trend_ref_close = Column(Float, nullable=True)
    trend_ref_value = Column(Float, nullable=True)

    details = Column(JSON)
    price_at_signal = Column(Float)
    stop_loss_price = Column(Float, nullable=True) 