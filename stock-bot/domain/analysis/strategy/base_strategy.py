from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import importlib

from infrastructure.db.models.enums import TrendType
from domain.analysis.config.strategy_settings import StrategyConfig, StrategyType, DetectorConfig
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.models.trading_signal import TradingSignal, SignalType
from infrastructure.logging import get_logger

logger = get_logger(__name__)

@dataclass
class StrategyResult:
    """전략 실행 결과"""
    strategy_name: str
    strategy_type: StrategyType
    has_signal: bool
    total_score: float
    signal_strength: str  # "WEAK", "MODERATE", "STRONG"
    signals_detected: List[str]
    signal: Optional[TradingSignal] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        """신호 강도 자동 계산"""
        if self.total_score >= 10:
            self.signal_strength = "STRONG"
        elif self.total_score >= 6:
            self.signal_strength = "MODERATE"
        else:
            self.signal_strength = "WEAK"
        
        self.confidence = min(self.total_score / 15.0, 1.0)  # 15점 만점 기준으로 정규화


class BaseStrategy(ABC):
    """전략 기본 클래스"""
    
    def __init__(self, strategy_type: StrategyType, config):
        self.strategy_type = strategy_type
        self.config = config
        self.orchestrator: Optional[SignalDetectionOrchestrator] = None
        self.is_initialized = False
        
        # 성능 모니터링
        self.signals_generated = 0
        self.last_analysis_time: Optional[datetime] = None
        self.average_score = 0.0
        self.score_history: List[float] = []
    
    def initialize(self) -> bool:
        """전략 초기화"""
        try:
            self.orchestrator = self._create_orchestrator()
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"{self.get_name()} 초기화 실패: {e}")
            return False
    
    @abstractmethod
    def _get_strategy_type(self) -> StrategyType:
        """전략 타입 반환"""
        pass
    
    @abstractmethod
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """오케스트레이터 생성"""
        pass
    
    def _create_detector_instance(self, detector_config: DetectorConfig):
        """감지기 인스턴스를 동적으로 생성"""
        try:
            # 감지기 클래스 매핑
            detector_class_mapping = {
                "SMASignalDetector": "domain.analysis.detectors.trend_following.sma_detector.SMASignalDetector",
                "MACDSignalDetector": "domain.analysis.detectors.trend_following.macd_detector.MACDSignalDetector",
                "RSISignalDetector": "domain.analysis.detectors.momentum.rsi_detector.RSISignalDetector",
                "StochSignalDetector": "domain.analysis.detectors.momentum.stoch_detector.StochSignalDetector",
                "VolumeSignalDetector": "domain.analysis.detectors.volume.volume_detector.VolumeSignalDetector",
                "ADXSignalDetector": "domain.analysis.detectors.trend_following.adx_detector.ADXSignalDetector",
                "CompositeSignalDetector": "domain.analysis.detectors.composite.composite_detector.CompositeSignalDetector",
            }
            
            if not detector_config.enabled:
                return None
            
            class_path = detector_class_mapping.get(detector_config.detector_class)
            if not class_path:
                logger.warning(f"알 수 없는 감지기 클래스: {detector_config.detector_class}")
                return None
            
            # 모듈과 클래스 분리
            module_path, class_name = class_path.rsplit('.', 1)
            
            # 모듈 동적 임포트
            module = importlib.import_module(module_path)
            detector_class = getattr(module, class_name)
            
            # 복합 감지기인 경우 특별 처리
            if detector_config.detector_class == "CompositeSignalDetector":
                return self._create_composite_detector(detector_config, detector_class)
            else:
                # 단일 감지기 생성
                return detector_class(detector_config.weight)
                
        except Exception as e:
            logger.error(f"감지기 생성 실패 {detector_config.detector_class}: {e}")
            return None
    
    def _create_composite_detector(self, detector_config: DetectorConfig, detector_class):
        """복합 감지기 생성"""
        params = detector_config.parameters
        composite_name = params.get("name", "Unknown")
        require_all = params.get("require_all", True)
        
        # 복합 감지기별 하위 감지기 정의
        sub_detectors = []
        
        if composite_name == "MACD_Volume_Confirm":
            # MACD + 거래량 조합
            from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector
            from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
            
            sub_detectors = [
                MACDSignalDetector(0),  # 가중치는 복합에서 설정
                VolumeSignalDetector(0)
            ]
        elif composite_name == "RSI_Stoch_Confirm":
            # RSI + 스토캐스틱 조합
            from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
            from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector
            
            sub_detectors = [
                RSISignalDetector(0),
                StochSignalDetector(0)
            ]
        elif composite_name == "Any_Momentum":
            # 모든 모멘텀 지표 조합
            from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
            from domain.analysis.detectors.momentum.stoch_detector import StochSignalDetector
            
            sub_detectors = [
                RSISignalDetector(0),
                StochSignalDetector(0)
            ]
        
        if sub_detectors:
            return detector_class(
                detectors=sub_detectors,
                weight=detector_config.weight,
                require_all=require_all,
                name=composite_name
            )
        else:
            logger.warning(f"복합 감지기 '{composite_name}'에 대한 하위 감지기를 찾을 수 없습니다.")
            return None
    
    def analyze(self, 
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Dict = None) -> StrategyResult:
        """신호 분석 실행"""
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")
        
        self.last_analysis_time = datetime.now()
        
        try:
            # 오케스트레이터로 신호 감지
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )
            
            # 전략별 점수 조정
            adjusted_score = self._adjust_score_by_strategy(
                signal_result.get('score', 0), market_trend, long_term_trend
            )
            
            # 성능 모니터링 업데이트
            self.score_history.append(adjusted_score)
            if len(self.score_history) > 100:  # 최근 100개만 유지
                self.score_history.pop(0)
            self.average_score = sum(self.score_history) / len(self.score_history)
            
            # 신호 여부 판단
            has_signal = adjusted_score >= self.config.signal_threshold
            
            if has_signal:
                self.signals_generated += 1
                
                # TradingSignal 객체 생성
                trading_signal = self._create_trading_signal(
                    signal_result, ticker, adjusted_score, df_with_indicators
                )
            else:
                trading_signal = None
            
            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=has_signal,
                total_score=adjusted_score,
                signal_strength="",  # __post_init__에서 자동 계산
                signals_detected=signal_result.get('details', []),
                signal=trading_signal
            )
            
        except Exception as e:
            logger.error(f"{self.get_name()} 분석 실패: {e}")
            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=False,
                total_score=0.0,
                signal_strength="WEAK",
                signals_detected=[],
                signal=None
            )
    
    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """전략별 점수 조정"""
        adjusted_score = base_score
        
        # 시장 추세에 따른 조정
        if market_trend == TrendType.BULLISH:
            if self.strategy_type in [StrategyType.AGGRESSIVE, StrategyType.MOMENTUM]:
                adjusted_score *= 1.2  # 상승장에서 공격적/모멘텀 전략 가산점
            elif self.strategy_type == StrategyType.CONTRARIAN:
                adjusted_score *= 0.8  # 상승장에서 역투자 전략 감점
        elif market_trend == TrendType.BEARISH:
            if self.strategy_type in [StrategyType.CONSERVATIVE, StrategyType.CONTRARIAN]:
                adjusted_score *= 1.1  # 하락장에서 보수적/역투자 전략 가산점
            elif self.strategy_type == StrategyType.AGGRESSIVE:
                adjusted_score *= 0.9  # 하락장에서 공격적 전략 감점
        
        return adjusted_score
    
    def _create_trading_signal(self, signal_result: Dict, ticker: str, score: float, 
                             df_with_indicators: pd.DataFrame) -> TradingSignal:
        """TradingSignal 객체 생성"""
        from domain.analysis.models.trading_signal import SignalEvidence
        
        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL
        
        evidence = SignalEvidence(
            signal_timestamp=datetime.now(),
            ticker=ticker,
            signal_type=signal_result.get('type', 'BUY'),
            final_score=int(score),
            raw_signals=signal_result.get('details', []),
            applied_filters=[f"Strategy: {self.get_name()}"],
            score_adjustments=[f"Strategy adjustment applied: {self.get_name()}"]
        )
        
        return TradingSignal(
            signal_id=None,
            ticker=ticker,
            signal_type=signal_type,
            signal_score=score,
            timestamp_utc=datetime.now(),
            current_price=df_with_indicators['Close'].iloc[-1],
            market_trend=signal_result.get('market_trend', 'NEUTRAL'),
            long_term_trend=signal_result.get('long_term_trend', 'NEUTRAL'),
            details=signal_result.get('details', []),
            stop_loss_price=signal_result.get('stop_loss_price'),
            evidence=evidence
        )
    
    def get_name(self) -> str:
        """전략 이름 반환"""
        return self.config.name
    
    def get_description(self) -> str:
        """전략 설명 반환"""
        return self.config.description
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """전략 성능 지표 반환"""
        return {
            'signals_generated': self.signals_generated,
            'average_score': self.average_score,
            'last_analysis_time': self.last_analysis_time,
            'score_history_length': len(self.score_history),
            'is_initialized': self.is_initialized,
            'signal_threshold': self.config.signal_threshold,
            'risk_per_trade': self.config.risk_per_trade
        }
    
    def reset_performance_metrics(self):
        """성능 지표 초기화"""
        self.signals_generated = 0
        self.score_history.clear()
        self.average_score = 0.0
        self.last_analysis_time = None
    
    def update_config(self, new_config: StrategyConfig) -> bool:
        """전략 설정을 업데이트합니다."""
        try:
            self.config = new_config
            # 오케스트레이터 재생성
            self.orchestrator = self._create_orchestrator()
            return True
        except Exception as e:
            print(f"전략 설정 업데이트 실패 {self.get_name()}: {e}")
            return False
    
    def can_generate_signal(self, current_time: datetime) -> bool:
        """현재 신호를 생성할 수 있는지 확인 (쿨다운 체크 등)"""
        if self.last_analysis_time is None:
            return True
        
        # 최소 간격 체크 (예: 5분)
        min_interval_minutes = 5
        time_diff = current_time - self.last_analysis_time
        return time_diff.total_seconds() >= min_interval_minutes * 60 