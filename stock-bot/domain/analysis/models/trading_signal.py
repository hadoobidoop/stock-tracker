from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from infrastructure.db.models.enums import TrendType, SignalType


@dataclass
class TechnicalIndicatorEvidence:
    """기술적 지표 근거"""
    indicator_name: str  # 예: "RSI_14", "MACD_12_26_9", "SMA_20"
    current_value: float
    previous_value: Optional[float] = None
    threshold_value: Optional[float] = None  # 임계값 (예: RSI 70, 30)
    condition_met: str = ""  # 만족한 조건 설명
    timeframe: str = "1h"  # 시간대 (1h, 1d)
    contribution_score: float = 0.0  # 이 지표가 전체 신호에 기여한 점수


@dataclass
class MultiTimeframeEvidence:
    """다중 시간대 분석 근거"""
    daily_trend: str  # BULLISH, BEARISH, NEUTRAL
    hourly_trend: str
    consensus: str  # BULLISH, BEARISH, MIXED, NEUTRAL
    daily_indicators: Dict[str, float] = field(default_factory=dict)  # 일봉 지표값들
    hourly_indicators: Dict[str, float] = field(default_factory=dict)  # 시간봉 지표값들
    confidence_adjustment: float = 1.0  # 신뢰도 조정 계수


@dataclass
class MarketContextEvidence:
    """시장 상황 근거"""
    market_trend: str  # 전체 시장 추세
    sector_performance: Optional[str] = None  # 섹터 성과 (향후 확장용)
    volatility_level: Optional[str] = None  # 변동성 수준 (HIGH, MEDIUM, LOW)
    volume_analysis: Optional[str] = None  # 거래량 분석


@dataclass
class RiskManagementEvidence:
    """리스크 관리 근거"""
    stop_loss_method: str  # 손절가 계산 방법 (예: "ATR_2x")
    stop_loss_percentage: float  # 손절 비율
    position_sizing_factor: Optional[float] = None  # 포지션 크기 조정 인자
    risk_reward_ratio: Optional[float] = None


@dataclass
class SignalEvidence:
    """종합적인 신호 근거"""
    
    # 기본 정보
    signal_timestamp: datetime
    ticker: str
    signal_type: str
    final_score: int
    
    # 상세 근거들
    technical_evidences: List[TechnicalIndicatorEvidence] = field(default_factory=list)
    multi_timeframe_evidence: Optional[MultiTimeframeEvidence] = None
    market_context_evidence: Optional[MarketContextEvidence] = None
    risk_management_evidence: Optional[RiskManagementEvidence] = None
    
    # 의사결정 과정
    raw_signals: List[str] = field(default_factory=list)  # 원본 신호 리스트
    applied_filters: List[str] = field(default_factory=list)  # 적용된 필터들
    score_adjustments: List[str] = field(default_factory=list)  # 점수 조정 내역
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 저장용 딕셔너리로 변환"""
        return {
            'signal_timestamp': self.signal_timestamp.isoformat(),
            'ticker': self.ticker,
            'signal_type': self.signal_type,
            'final_score': self.final_score,
            'technical_evidences': [
                {
                    'indicator_name': te.indicator_name,
                    'current_value': te.current_value,
                    'previous_value': te.previous_value,
                    'threshold_value': te.threshold_value,
                    'condition_met': te.condition_met,
                    'timeframe': te.timeframe,
                    'contribution_score': te.contribution_score
                } for te in self.technical_evidences
            ],
            'multi_timeframe_evidence': {
                'daily_trend': self.multi_timeframe_evidence.daily_trend,
                'hourly_trend': self.multi_timeframe_evidence.hourly_trend,
                'consensus': self.multi_timeframe_evidence.consensus,
                'daily_indicators': self.multi_timeframe_evidence.daily_indicators,
                'hourly_indicators': self.multi_timeframe_evidence.hourly_indicators,
                'confidence_adjustment': self.multi_timeframe_evidence.confidence_adjustment
            } if self.multi_timeframe_evidence else None,
            'market_context_evidence': {
                'market_trend': self.market_context_evidence.market_trend,
                'sector_performance': self.market_context_evidence.sector_performance,
                'volatility_level': self.market_context_evidence.volatility_level,
                'volume_analysis': self.market_context_evidence.volume_analysis
            } if self.market_context_evidence else None,
            'risk_management_evidence': {
                'stop_loss_method': self.risk_management_evidence.stop_loss_method,
                'stop_loss_percentage': self.risk_management_evidence.stop_loss_percentage,
                'position_sizing_factor': self.risk_management_evidence.position_sizing_factor,
                'risk_reward_ratio': self.risk_management_evidence.risk_reward_ratio
            } if self.risk_management_evidence else None,
            'raw_signals': self.raw_signals,
            'applied_filters': self.applied_filters,
            'score_adjustments': self.score_adjustments
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalEvidence':
        """딕셔너리에서 객체 생성"""
        evidence = cls(
            signal_timestamp=datetime.fromisoformat(data['signal_timestamp']),
            ticker=data['ticker'],
            signal_type=data['signal_type'],
            final_score=data['final_score'],
            raw_signals=data.get('raw_signals', []),
            applied_filters=data.get('applied_filters', []),
            score_adjustments=data.get('score_adjustments', [])
        )
        
        # 기술적 지표 근거 복원
        for te_data in data.get('technical_evidences', []):
            te = TechnicalIndicatorEvidence(
                indicator_name=te_data['indicator_name'],
                current_value=te_data['current_value'],
                previous_value=te_data.get('previous_value'),
                threshold_value=te_data.get('threshold_value'),
                condition_met=te_data.get('condition_met', ''),
                timeframe=te_data.get('timeframe', '1h'),
                contribution_score=te_data.get('contribution_score', 0.0)
            )
            evidence.technical_evidences.append(te)
        
        # 다중 시간대 근거 복원
        if data.get('multi_timeframe_evidence'):
            mte_data = data['multi_timeframe_evidence']
            evidence.multi_timeframe_evidence = MultiTimeframeEvidence(
                daily_trend=mte_data['daily_trend'],
                hourly_trend=mte_data['hourly_trend'],
                consensus=mte_data['consensus'],
                daily_indicators=mte_data.get('daily_indicators', {}),
                hourly_indicators=mte_data.get('hourly_indicators', {}),
                confidence_adjustment=mte_data.get('confidence_adjustment', 1.0)
            )
        
        # 시장 상황 근거 복원
        if data.get('market_context_evidence'):
            mce_data = data['market_context_evidence']
            evidence.market_context_evidence = MarketContextEvidence(
                market_trend=mce_data['market_trend'],
                sector_performance=mce_data.get('sector_performance'),
                volatility_level=mce_data.get('volatility_level'),
                volume_analysis=mce_data.get('volume_analysis')
            )
        
        # 리스크 관리 근거 복원
        if data.get('risk_management_evidence'):
            rme_data = data['risk_management_evidence']
            evidence.risk_management_evidence = RiskManagementEvidence(
                stop_loss_method=rme_data['stop_loss_method'],
                stop_loss_percentage=rme_data['stop_loss_percentage'],
                position_sizing_factor=rme_data.get('position_sizing_factor'),
                risk_reward_ratio=rme_data.get('risk_reward_ratio')
            )
        
        return evidence


@dataclass
class TradingSignal:
    """거래 신호 도메인 모델"""
    
    ticker: str
    signal_type: SignalType
    signal_score: int
    timestamp_utc: datetime
    current_price: float
    
    # 추세 정보
    market_trend: TrendType
    long_term_trend: Optional[TrendType] = None
    trend_ref_close: Optional[float] = None
    trend_ref_value: Optional[float] = None
    
    # 신호 상세 정보
    details: List[str] = field(default_factory=list)
    stop_loss_price: Optional[float] = None
    
    # 신호 근거 상세 정보 (새로 추가)
    evidence: Optional[SignalEvidence] = None
    
    # 메타데이터
    signal_id: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.signal_id is None:
            self.signal_id = f"signal_{self.ticker}_{int(self.timestamp_utc.timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """도메인 모델을 딕셔너리로 변환합니다."""
        return {
            'signal_id': self.signal_id,
            'ticker': self.ticker,
            'signal_type': self.signal_type,
            'signal_score': self.signal_score,
            'timestamp_utc': self.timestamp_utc,
            'current_price': self.current_price,
            'market_trend': self.market_trend,
            'long_term_trend': self.long_term_trend,
            'trend_ref_close': self.trend_ref_close,
            'trend_ref_value': self.trend_ref_value,
            'details': self.details,
            'stop_loss_price': self.stop_loss_price,
            'evidence': self.evidence.to_dict() if self.evidence else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """딕셔너리에서 도메인 모델을 생성합니다."""
        return cls(
            signal_id=data.get('signal_id'),
            ticker=data['ticker'],
            signal_type=data['signal_type'],
            signal_score=data['signal_score'],
            timestamp_utc=data['timestamp_utc'],
            current_price=data['current_price'],
            market_trend=data['market_trend'],
            long_term_trend=data.get('long_term_trend'),
            trend_ref_close=data.get('trend_ref_close'),
            trend_ref_value=data.get('trend_ref_value'),
            details=data.get('details', []),
            stop_loss_price=data.get('stop_loss_price'),
            evidence=SignalEvidence.from_dict(data['evidence']) if data.get('evidence') else None
        )
    
    def is_buy_signal(self) -> bool:
        """매수 신호인지 확인합니다."""
        return self.signal_type == SignalType.BUY
    
    def is_sell_signal(self) -> bool:
        """매도 신호인지 확인합니다."""
        return self.signal_type == SignalType.SELL
    
    def get_risk_reward_ratio(self) -> Optional[float]:
        """위험 대비 수익 비율을 계산합니다."""
        if self.stop_loss_price is None:
            return None
        
        if self.is_buy_signal():
            # 매수 신호: (목표가 - 현재가) / (현재가 - 손절가)
            # 목표가는 현재가의 2배로 가정
            target_price = self.current_price * 2
            return (target_price - self.current_price) / (self.current_price - self.stop_loss_price)
        else:
            # 매도 신호: (현재가 - 목표가) / (손절가 - 현재가)
            # 목표가는 현재가의 절반으로 가정
            target_price = self.current_price * 0.5
            return (self.current_price - target_price) / (self.stop_loss_price - self.current_price)
    
    def get_signal_strength(self) -> str:
        """신호 강도를 반환합니다."""
        if self.signal_score >= 15:
            return "STRONG"
        elif self.signal_score >= 10:
            return "MEDIUM"
        else:
            return "WEAK" 