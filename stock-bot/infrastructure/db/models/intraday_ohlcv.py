from sqlalchemy import Column, String, Float, DateTime, BigInteger, PrimaryKeyConstraint
from infrastructure.db.config.settings import Base


class IntradayOhlcv(Base):
    """
    순수한 1분봉 원시 데이터(OHLCV)를 저장하는 테이블.
    데이터의 '단일 진실 공급원(Single Source of Truth)' 역할을 합니다.
    """
    __tablename__ = 'intraday_ohlcv'

    # 복합 기본 키 (Composite Primary Key) 설정
    # 특정 종목의 특정 시간에는 단 하나의 데이터만 존재해야 함을 보장합니다.
    timestamp_utc = Column(DateTime, primary_key=True)
    ticker = Column(String(10), primary_key=True)

    # OHLCV 데이터
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    
    # 데이터 간격 (예: '1m', '5m', '15m', '1h')
    interval = Column(String(5), nullable=False, default='1m')

    # SQLAlchemy를 위한 명시적 제약 조건 정의
    __table_args__ = (
        PrimaryKeyConstraint('timestamp_utc', 'ticker'),
        {},
    ) 