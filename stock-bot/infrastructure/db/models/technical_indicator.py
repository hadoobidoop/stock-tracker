from sqlalchemy import Column, String, Float, DateTime, PrimaryKeyConstraint
from infrastructure.db.db_manager import Base


class TechnicalIndicator(Base):
    """
    계산된 기술적 지표 값만 저장하는 테이블.
    OHLCV 원본 데이터 컬럼은 IntradayOhlcv 테이블로 분리되어 제거되었습니다.
    """
    __tablename__ = 'technical_indicators'

    # 복합 기본 키 설정
    timestamp_utc = Column(DateTime, primary_key=True, index=True)
    ticker = Column(String(10), primary_key=True, index=True)

    # data_interval 컬럼은 어떤 시간 간격의 지표인지 명시 (예: '1m', '5m')
    data_interval = Column(String(5))

    # 기술적 지표 컬럼들
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
    kcle_20_2 = Column(Float, nullable=True)
    kcbe_20_2 = Column(Float, nullable=True)
    kcue_20_2 = Column(Float, nullable=True)
    atrr_14 = Column(Float, nullable=True)
    volume_sma_20 = Column(Float, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('timestamp_utc', 'ticker'),
        {},
    ) 