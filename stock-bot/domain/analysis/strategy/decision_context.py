"""
DecisionContext - 동적 가중치 조절 시스템의 핵심 컨텍스트 클래스

모든 판단의 재료와 중간 과정을 담는 그릇 역할을 합니다.
전략의 기본 가중치, 각 Detector의 값, Modifier에 의해 변경된 최종 가중치 등을 모두 관리합니다.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import copy

from domain.analysis.config.dynamic_strategies import ModifierActionType
from domain.analysis.models.trading_signal import SignalType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WeightAdjustment:
    """가중치 조정 기록"""
    detector_name: str
    original_weight: float
    adjustment: float
    final_weight: float
    modifier_name: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModifierApplication:
    """Modifier 적용 기록"""
    modifier_name: str
    modifier_type: str  # 'FILTER', 'ADJUSTMENT' 등
    applied: bool
    reason: str
    original_score: Optional[float] = None
    adjusted_score: Optional[float] = None
    original_weight: Optional[float] = None
    adjusted_weight: Optional[float] = None


@dataclass
class DecisionLog:
    """의사결정 로그"""
    step: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class DecisionContext:
    """
    판단의 모든 과정을 담는 컨텍스트 객체
    
    이 클래스는 다음과 같은 정보를 관리합니다:
    1. 기본 가중치와 조정된 가중치
    2. 각 detector의 원시 점수와 조정된 점수
    3. 모디파이어 적용 내역
    4. 최종 판단 결과
    5. 상세한 로깅 정보
    """
    
    def __init__(self, strategy_config: Dict[str, Any]):
        # 전략 기본 설정
        self.strategy_name = strategy_config.get("description", "Unknown Strategy")
        self.base_threshold = strategy_config.get("signal_threshold", 8.0)
        self.risk_per_trade = strategy_config.get("risk_per_trade", 0.02)
        
        # 가중치 관리
        self.original_weights = {
            name: params['weight'] 
            for name, params in strategy_config['detectors'].items()
        }
        self.current_weights = copy.deepcopy(self.original_weights)
        self.weight_adjustments: List[WeightAdjustment] = []
        
        # 점수 관리
        self.detector_raw_scores: Dict[str, float] = {}
        self.detector_weighted_scores: Dict[str, float] = {}
        self.total_raw_score = 0.0
        self.total_weighted_score = 0.0
        self.final_score = 0.0
        
        # 임계값 및 배율 조정
        self.current_threshold = self.base_threshold
        self.threshold_adjustments: List[float] = []
        self.score_multipliers: List[float] = []
        
        # 거부(Veto) 상태
        self.is_vetoed = False
        self.veto_reason = ""
        self.veto_type: Optional[ModifierActionType] = None
        
        # 모디파이어 적용 기록
        self.modifier_applications: List[ModifierApplication] = []
        
        # 결정 로그
        self.decision_logs: List[DecisionLog] = []
        
        # 메타데이터
        self.creation_time = datetime.now()
        self.ticker = ""
        self.market_data: Dict[str, Any] = {}
        
    def log_decision(self, step: str, action: str, details: Dict[str, Any] = None):
        """의사결정 과정 로깅"""
        if details is None:
            details = {}
        
        log_entry = DecisionLog(
            step=step,
            action=action,
            details=details
        )
        self.decision_logs.append(log_entry)
        
        logger.debug(f"DecisionContext [{self.ticker}] {step}: {action} - {details}")
    
    def set_detector_score(self, detector_name: str, raw_score: float):
        """detector의 원시 점수 설정"""
        self.detector_raw_scores[detector_name] = raw_score
        self.log_decision(
            "SCORE_INPUT", 
            f"Set {detector_name} raw score",
            {"detector": detector_name, "raw_score": raw_score}
        )
    
    def adjust_weight(self, detector_name: str, adjustment: float, modifier_name: str, reason: str):
        """가중치 조정"""
        if detector_name not in self.current_weights:
            logger.warning(f"Detector '{detector_name}' not found in weights")
            return
        
        original_weight = self.current_weights[detector_name]
        new_weight = max(0.0, original_weight + adjustment)  # 0 미만으로 떨어지지 않도록
        
        # 조정 기록
        weight_adjustment = WeightAdjustment(
            detector_name=detector_name,
            original_weight=original_weight,
            adjustment=adjustment,
            final_weight=new_weight,
            modifier_name=modifier_name,
            reason=reason
        )
        self.weight_adjustments.append(weight_adjustment)
        
        # 가중치 업데이트
        self.current_weights[detector_name] = new_weight
        
        self.log_decision(
            "WEIGHT_ADJUSTMENT",
            f"Adjusted {detector_name} weight",
            {
                "detector": detector_name,
                "original": original_weight,
                "adjustment": adjustment,
                "final": new_weight,
                "modifier": modifier_name,
                "reason": reason
            }
        )
    
    def adjust_threshold(self, adjustment: float, modifier_name: str, reason: str):
        """임계값 조정"""
        self.threshold_adjustments.append(adjustment)
        self.current_threshold += adjustment
        
        self.log_decision(
            "THRESHOLD_ADJUSTMENT",
            f"Adjusted threshold by {adjustment}",
            {
                "adjustment": adjustment,
                "new_threshold": self.current_threshold,
                "modifier": modifier_name,
                "reason": reason
            }
        )
    
    def apply_score_multiplier(self, multiplier: float, modifier_name: str, reason: str):
        """점수 배율 적용"""
        self.score_multipliers.append(multiplier)
        
        self.log_decision(
            "SCORE_MULTIPLIER",
            f"Applied score multiplier {multiplier}",
            {
                "multiplier": multiplier,
                "modifier": modifier_name,
                "reason": reason
            }
        )
    
    def set_veto(self, veto_type: ModifierActionType, reason: str, modifier_name: str):
        """거부(Veto) 상태 설정"""
        self.is_vetoed = True
        self.veto_reason = reason
        self.veto_type = veto_type
        
        self.log_decision(
            "VETO_APPLIED",
            f"Trade vetoed: {veto_type.value}",
            {
                "veto_type": veto_type.value,
                "reason": reason,
                "modifier": modifier_name
            }
        )
    
    def record_modifier_application(self, modifier_name: str, modifier_type: str,
                                   applied: bool, reason: str, details: Dict[str, Any] = None):
        """모디파이어 적용 기록"""
        if details is None:
            details = {}

        application = ModifierApplication(
            modifier_name=modifier_name,
            modifier_type=modifier_type,
            applied=applied,
            reason=reason,
            **details
        )
        self.modifier_applications.append(application)
    
    def calculate_weighted_scores(self):
        """가중치가 적용된 점수 계산"""
        self.detector_weighted_scores = {}
        self.total_weighted_score = 0.0
        
        for detector_name, raw_score in self.detector_raw_scores.items():
            weight = self.current_weights.get(detector_name, 0.0)
            weighted_score = raw_score * weight
            
            self.detector_weighted_scores[detector_name] = weighted_score
            self.total_weighted_score += weighted_score
        
        self.log_decision(
            "WEIGHTED_SCORE_CALCULATION",
            "Calculated weighted scores",
            {
                "detector_scores": self.detector_weighted_scores,
                "total_weighted_score": self.total_weighted_score
            }
        )
    
    def calculate_final_score(self):
        """최종 점수 계산 (배율 적용)"""
        if not self.detector_weighted_scores:
            self.calculate_weighted_scores()
        
        self.final_score = self.total_weighted_score
        
        # 점수 배율 적용
        for multiplier in self.score_multipliers:
            self.final_score *= multiplier
        
        self.log_decision(
            "FINAL_SCORE_CALCULATION", 
            "Calculated final score",
            {
                "weighted_score": self.total_weighted_score,
                "multipliers": self.score_multipliers,
                "final_score": self.final_score,
                "threshold": self.current_threshold
            }
        )
    
    def should_generate_buy_signal(self) -> bool:
        """매수 신호 생성 여부 판단"""
        if self.is_vetoed and self.veto_type in [ModifierActionType.VETO_BUY, ModifierActionType.VETO_ALL]:
            return False
        return self.final_score >= self.current_threshold
    
    def should_generate_sell_signal(self) -> bool:
        """매도 신호 생성 여부 판단"""
        if self.is_vetoed and self.veto_type in [ModifierActionType.VETO_SELL, ModifierActionType.VETO_ALL]:
            return False
        return self.final_score <= -self.current_threshold
    
    def get_signal_type(self) -> SignalType:
        """최종 신호 타입 결정"""
        if self.should_generate_buy_signal():
            return SignalType.BUY
        elif self.should_generate_sell_signal():
            return SignalType.SELL
        else:
            return SignalType.NEUTRAL
    
    def get_signal_strength(self) -> str:
        """신호 강도 계산"""
        abs_score = abs(self.final_score)
        if abs_score >= self.current_threshold * 1.5:
            return "STRONG"
        elif abs_score >= self.current_threshold:
            return "MODERATE"
        else:
            return "WEAK"
    
    def get_confidence(self) -> float:
        """신뢰도 계산 (0.0 ~ 1.0)"""
        max_possible_score = self.current_threshold * 2
        return min(abs(self.final_score) / max_possible_score, 1.0)
    
    def get_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약 정보 반환"""
        return {
            "strategy_name": self.strategy_name,
            "ticker": self.ticker,
            "creation_time": self.creation_time.isoformat(),
            
            # 가중치 정보
            "original_weights": self.original_weights,
            "final_weights": self.current_weights,
            "weight_changes": len(self.weight_adjustments),
            
            # 점수 정보
            "raw_scores": self.detector_raw_scores,
            "weighted_scores": self.detector_weighted_scores,
            "total_weighted_score": self.total_weighted_score,
            "final_score": self.final_score,
            
            # 임계값 정보
            "base_threshold": self.base_threshold,
            "final_threshold": self.current_threshold,
            "threshold_adjustments": self.threshold_adjustments,
            
            # 배율 정보
            "score_multipliers": self.score_multipliers,
            
            # 거부 정보
            "is_vetoed": self.is_vetoed,
            "veto_reason": self.veto_reason,
            "veto_type": self.veto_type.value if self.veto_type else None,
            
            # 결과 정보
            "signal_type": self.get_signal_type().value,
            "signal_strength": self.get_signal_strength(),
            "confidence": self.get_confidence(),
            
            # 모디파이어 정보
            "modifiers_applied": len([m for m in self.modifier_applications if m.applied]),
            "total_modifiers_evaluated": len(self.modifier_applications)
        }
    
    def get_detailed_log(self) -> List[Dict[str, Any]]:
        """상세 로그 반환"""
        return [
            {
                "step": log.step,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            }
            for log in self.decision_logs
        ] 