from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Text


@dataclass
class StockMetadata:
    """
    종목의 메타데이터를 나타내는 도메인 모델.
    DB의 특정 필드 이름이 아닌, 비즈니스 로직에서 사용할 용어로 정의합니다.
    """
    ticker: str
    company_name: str
    exchange: str
    is_active: bool = True
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    quote_type: Optional[str] = None  # 증권 종류 (EQUITY, ETF 등)
    currency: Optional[str] = None  # 거래 통화
    market_cap: Optional[int] = None  # 시가 총액 (BigInteger -> int)
    shares_outstanding: Optional[int] = None  # 발행 주식 수
    beta: Optional[float] = None  # 베타 계수
    dividend_yield: Optional[float] = None  # 배당 수익률
    logo_url: Optional[str] = None  # 회사 로고 URL
    long_business_summary: Optional[Text] = None  # 상세 사업 내용
    
    need_analysis: bool = True  # 분석 필요 여부

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
