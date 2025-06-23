"""
시장 전체 지표 데이터를 저장하는 모델
버핏 지수, VIX, 공포지수 등 개별 종목이 아닌 시장 전체의 지표들을 관리합니다.
"""
from sqlalchemy import Column, Integer, String, Float, Date, Enum as SQLEnum, DateTime, Text
from infrastructure.db.db_manager import Base
from datetime import datetime

from .enums import MarketIndicatorType


class MarketData(Base):
    __tablename__ = 'market_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment="지표 날짜")
    indicator_type = Column(SQLEnum(MarketIndicatorType), nullable=False, index=True, comment="지표 타입")
    value = Column(Float, nullable=False, comment="지표 값")
    additional_data = Column(Text, nullable=True, comment="추가 메타데이터 (JSON 형태)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="생성 시간")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정 시간")

    def __repr__(self):
        return f"<MarketData(date='{self.date}', indicator='{self.indicator_type.value}', value={self.value})>"

    def to_dict(self):
        """객체를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'indicator_type': self.indicator_type.value,
            'value': self.value,
            'additional_data': self.additional_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 