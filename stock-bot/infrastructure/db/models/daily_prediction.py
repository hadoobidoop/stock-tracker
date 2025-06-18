from sqlalchemy import Column, String, Integer, Float, DateTime, Date, JSON
from infrastructure.db.config.settings import Base


class DailyPrediction(Base):
    """일일 예측 테이블"""
    __tablename__ = 'daily_predictions'
    
    prediction_id = Column(String(36), primary_key=True)  # UUID는 36자
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