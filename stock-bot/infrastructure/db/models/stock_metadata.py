from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Float, DateTime, Text
from sqlalchemy.sql import func
from infrastructure.db.config.settings import Base


class StockMetadata(Base):
    """주식 메타데이터 테이블"""
    __tablename__ = 'stock_metadata'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String(10), primary_key=True)
    company_name = Column(String(255))
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    # 상세 메타데이터 컬럼
    quote_type = Column(String(20), nullable=True)  # 증권 종류 (EQUITY, ETF 등)
    currency = Column(String(10), nullable=True)  # 거래 통화
    market_cap = Column(BigInteger, nullable=True)  # 시가 총액
    shares_outstanding = Column(BigInteger, nullable=True)  # 발행 주식 수
    beta = Column(Float, nullable=True)  # 베타 계수
    dividend_yield = Column(Float, nullable=True)  # 배당 수익률
    logo_url = Column(String(255), nullable=True)  # 회사 로고 URL
    long_business_summary = Column(Text, nullable=True)  # 상세 사업 내용 (긴 텍스트)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    need_analysis = Column(Boolean, default=True, nullable=False) 