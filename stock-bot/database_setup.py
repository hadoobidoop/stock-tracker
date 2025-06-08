import enum
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, Enum, BigInteger, JSON, \
    Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
# config 파일에서 수정된 DATABASE_URL을 가져옵니다.
from config import DATABASE_URL

# --- 데이터베이스 엔진 및 세션 설정 ---
# connect_args를 통해 추가적인 연결 옵션을 설정할 수 있습니다.
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 테이블 모델 정의 (변경 없음) ---

class StockMetadata(Base):
    __tablename__ = 'stock_metadata'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String(10), primary_key=True)
    company_name = Column(String(255))
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    # --- [신규 추가] 상세 메타데이터 컬럼 ---
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


class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    timestamp_utc = Column(DateTime, index=True)
    ticker = Column(String(10), index=True)
    data_interval = Column(String(5))
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    sma_5 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_60 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd_12_26_9 = Column(Float, nullable=True)
    macds_12_26_9 = Column(Float, nullable=True)
    macdh_12_26_9 = Column(Float, nullable=True)
    stochk_14_3_3 = Column(Float, nullable=True)
    stochd_14_3_3 = Column(Float, nullable=True)
    adx_14 = Column(Float, nullable=True)
    dmp_14 = Column(Float, nullable=True)
    dmn_14 = Column(Float, nullable=True)
    bbl_20_2_0 = Column(Float, nullable=True)
    bbm_20_2_0 = Column(Float, nullable=True)
    bbu_20_2_0 = Column(Float, nullable=True)
    kcle_20_2_0 = Column(Float, nullable=True)
    kcbe_20_2_0 = Column(Float, nullable=True)
    kcue_20_2_0 = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    volume_sma_20 = Column(Float, nullable=True)


class TrendType(str, enum.Enum):
    """[신규] 추세의 종류를 정의하는 Enum 클래스"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class TradingSignal(Base):
    __tablename__ = 'trading_signals'
    signal_id = Column(String(36), primary_key=True)  # UUID는 36자
    timestamp_utc = Column(DateTime, index=True)
    ticker = Column(String(10), index=True)
    signal_type = Column(Enum(SignalType))
    signal_score = Column(Integer)

    market_trend = Column(Enum(TrendType))  # S&P 500 기준 전체 시장 추세
    long_term_trend = Column(Enum(TrendType), nullable=True)  # 개별 종목의 장기 추세 상태 (1h)
    trend_ref_close = Column(Float, nullable=True)  # 장기 추세 판단 시 사용된 1h 종가
    trend_ref_value = Column(Float, nullable=True)  # 장기 추세 판단 시 사용된 1h 이평선 값

    details = Column(JSON)
    price_at_signal = Column(Float)
    stop_loss_price = Column(Float, nullable=True)


class DailyPrediction(Base):
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


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
    print("Database and tables checked/created successfully for MySQL.")


if __name__ == "__main__":
    create_db_and_tables()
