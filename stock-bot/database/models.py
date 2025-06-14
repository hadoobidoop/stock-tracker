# stock_bot/database/models.py
# 역할: 데이터베이스의 모든 테이블 구조(스키마)를 SQLAlchemy 모델 클래스로 정의합니다.
# 기존 database_setup.py의 모델 정의 부분을 그대로 가져옵니다.

from sqlalchemy import (Column, Integer, String, Float, DateTime, Date,
                        Boolean, Enum as SQLAlchemyEnum, BigInteger, JSON, Text,
                        PrimaryKeyConstraint)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import enum

# 모든 모델이 상속받을 기본 클래스
Base = declarative_base()

# 데이터베이스와 파이썬 코드 양쪽에서 사용할 Enum 정의
class TrendType(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


# --- 테이블 모델 정의 ---

class IntradayOhlcv(Base):
    __tablename__ = 'intraday_ohlcv'
    timestamp_utc = Column(DateTime, primary_key=True)
    ticker = Column(String(10), primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    interval = Column(String(5), nullable=False, default='1m')
    __table_args__ = (PrimaryKeyConstraint('timestamp_utc', 'ticker'),)

class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'
    timestamp_utc = Column(DateTime, primary_key=True, index=True)
    ticker = Column(String(10), primary_key=True, index=True)
    data_interval = Column(String(5))
    sma_5 = Column(Float, nullable=True)
    # ... 기존 파일에 있던 모든 지표 컬럼들 ...
    volume_sma_20 = Column(Float, nullable=True)
    __table_args__ = (PrimaryKeyConstraint('timestamp_utc', 'ticker'),)

class StockMetadata(Base):
    __tablename__ = 'stock_metadata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False)
    company_name = Column(String(255))
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    quote_type = Column(String(20), nullable=True)
    currency = Column(String(10), nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    shares_outstanding = Column(BigInteger, nullable=True)
    beta = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    logo_url = Column(String(255), nullable=True)
    long_business_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    need_analysis = Column(Boolean, default=True, nullable=False)

class TradingSignal(Base):
    __tablename__ = 'trading_signals'
    signal_id = Column(String(36), primary_key=True)
    timestamp_utc = Column(DateTime, index=True)
    ticker = Column(String(10), index=True)
    signal_type = Column(SQLAlchemyEnum(SignalType))
    signal_score = Column(Integer)
    market_trend = Column(SQLAlchemyEnum(TrendType))
    long_term_trend = Column(SQLAlchemyEnum(TrendType), nullable=True)
    trend_ref_close = Column(Float, nullable=True)
    trend_ref_value = Column(Float, nullable=True)
    details = Column(JSON)
    price_at_signal = Column(Float)
    stop_loss_price = Column(Float, nullable=True)

class DailyPrediction(Base):
    __tablename__ = 'daily_predictions'
    prediction_id = Column(String(36), primary_key=True)
    prediction_date_utc = Column(Date, index=True)
    generated_at_utc = Column(DateTime)
    ticker = Column(String(10), index=True)
    predicted_price_type = Column(String(50))
    predicted_price = Column(Float)
    predicted_range_low = Column(Float)
    predicted_range_high = Column(Float)
    reason = Column(String(255), nullable=True)
    prediction_score = Column(Integer)
    details = Column(JSON)
    prev_day_close = Column(Float)

