from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class TechnicalIndicator:
    """기술적 지표 도메인 모델"""
    
    timestamp_utc: datetime
    ticker: str
    data_interval: str
    
    # 이동평균
    sma_5: Optional[float] = None
    sma_20: Optional[float] = None
    sma_60: Optional[float] = None
    
    # RSI
    rsi_14: Optional[float] = None
    
    # MACD
    macd_12_26_9: Optional[float] = None
    macds_12_26_9: Optional[float] = None
    macdh_12_26_9: Optional[float] = None
    
    # 스토캐스틱
    stochk_14_3_3: Optional[float] = None
    stochd_14_3_3: Optional[float] = None
    
    # ADX
    adx_14: Optional[float] = None
    dmp_14: Optional[float] = None
    dmn_14: Optional[float] = None
    
    # 볼린저 밴드
    bbl_20_2_0: Optional[float] = None
    bbm_20_2_0: Optional[float] = None
    bbu_20_2_0: Optional[float] = None
    
    # ATR
    atrr_14: Optional[float] = None
    
    # 거래량
    volume_sma_20: Optional[float] = None
    
    # 추가 지표들을 위한 확장 필드
    additional_indicators: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """도메인 모델을 딕셔너리로 변환합니다."""
        return {
            'timestamp_utc': self.timestamp_utc,
            'ticker': self.ticker,
            'data_interval': self.data_interval,
            'sma_5': self.sma_5,
            'sma_20': self.sma_20,
            'sma_60': self.sma_60,
            'rsi_14': self.rsi_14,
            'macd_12_26_9': self.macd_12_26_9,
            'macds_12_26_9': self.macds_12_26_9,
            'macdh_12_26_9': self.macdh_12_26_9,
            'stochk_14_3_3': self.stochk_14_3_3,
            'stochd_14_3_3': self.stochd_14_3_3,
            'adx_14': self.adx_14,
            'dmp_14': self.dmp_14,
            'dmn_14': self.dmn_14,
            'bbl_20_2_0': self.bbl_20_2_0,
            'bbm_20_2_0': self.bbm_20_2_0,
            'bbu_20_2_0': self.bbu_20_2_0,
            'atrr_14': self.atrr_14,
            'volume_sma_20': self.volume_sma_20,
            'additional_indicators': self.additional_indicators
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TechnicalIndicator':
        """딕셔너리에서 도메인 모델을 생성합니다."""
        return cls(
            timestamp_utc=data['timestamp_utc'],
            ticker=data['ticker'],
            data_interval=data['data_interval'],
            sma_5=data.get('sma_5'),
            sma_20=data.get('sma_20'),
            sma_60=data.get('sma_60'),
            rsi_14=data.get('rsi_14'),
            macd_12_26_9=data.get('macd_12_26_9'),
            macds_12_26_9=data.get('macds_12_26_9'),
            macdh_12_26_9=data.get('macdh_12_26_9'),
            stochk_14_3_3=data.get('stochk_14_3_3'),
            stochd_14_3_3=data.get('stochd_14_3_3'),
            adx_14=data.get('adx_14'),
            dmp_14=data.get('dmp_14'),
            dmn_14=data.get('dmn_14'),
            bbl_20_2_0=data.get('bbl_20_2_0'),
            bbm_20_2_0=data.get('bbm_20_2_0'),
            bbu_20_2_0=data.get('bbu_20_2_0'),
            atrr_14=data.get('atrr_14'),
            volume_sma_20=data.get('volume_sma_20'),
            additional_indicators=data.get('additional_indicators', {})
        ) 