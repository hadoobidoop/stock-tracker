"""
DynamicCompositeStrategy - 동적 가중치 조절 전략

거시 경제 상황에 따라 기술적 지표의 가중치를 동적으로 변경하는 지능형 전략입니다.
DecisionContext를 사용하여 모든 판단 과정을 추적하고, Modifier들을 순서대로 적용합니다.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import importlib

from .base_strategy import BaseStrategy, StrategyResult
from .decision_context import DecisionContext
from .modifier_engine import ModifierEngine
from domain.analysis.models.trading_signal import (
    TradingSignal, SignalType, SignalEvidence, TechnicalIndicatorEvidence, MarketContextEvidence
)
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ..config import StrategyType

logger = get_logger(__name__)


class DynamicCompositeStrategy(BaseStrategy):
    """
    동적 가중치 조절 전략
    - 팩토리에서 생성 시 모든 의존성이 주입됩니다.
    """
    REQUIRED_MACRO_INDICATORS: List[str] = []
    
    def __init__(self, 
                 strategy_name: str, 
                 strategy_config: Dict[str, Any],
                 modifier_engine: ModifierEngine):
        
        self.strategy_name = strategy_name
        self.strategy_config = strategy_config
        self.modifier_engine = modifier_engine
        
        # BaseStrategy 초기화를 위한 더미 config 생성
        from domain.analysis.config.static_strategies import StrategyConfig
        dummy_config = StrategyConfig(
            name=self.strategy_name,
            description=self.strategy_config.get("description", ""),
            signal_threshold=self.strategy_config.get("signal_threshold", 8.0),
            risk_per_trade=self.strategy_config.get("risk_per_trade", 0.02),
            detectors=[]
        )
        super().__init__(StrategyType.MACRO_DRIVEN, dummy_config)
        
        self.technical_detectors: Dict[str, Any] = {}
        self.last_context: Optional[DecisionContext] = None

    def get_required_macro_indicators(self) -> List[str]:
        """이 전략의 실행에 필요한 거시 지표 목록을 반환합니다."""
        required = set(self.REQUIRED_MACRO_INDICATORS)
        for modifier in self.modifier_engine.modifiers:
            required.add(modifier.definition.detector)
        return list(required)
        
    def _get_strategy_type(self) -> 'StrategyType':
        return StrategyType.MACRO_DRIVEN
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """기술적 지표 detector들을 위한 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_name, detector_config in self.strategy_config.get("detectors", {}).items():
            detector = self._create_technical_detector(detector_name, detector_config)
            if detector:
                orchestrator.add_detector(detector)
                self.technical_detectors[detector_name] = detector
        return orchestrator
    
    def _create_technical_detector(self, detector_name: str, detector_config: Dict[str, Any]):
        """기술적 지표 detector 생성"""
        try:
            detector_class_mapping = {
                "rsi": "domain.analysis.detectors.momentum.rsi_detector.RSISignalDetector",
                "macd": "domain.analysis.detectors.trend_following.macd_detector.MACDSignalDetector",
                "sma": "domain.analysis.detectors.trend_following.sma_detector.SMASignalDetector",
                "stoch": "domain.analysis.detectors.momentum.stoch_detector.StochSignalDetector",
                "adx": "domain.analysis.detectors.trend_following.adx_detector.ADXSignalDetector",
                "volume": "domain.analysis.detectors.volume.volume_detector.VolumeSignalDetector",
                "bb": "domain.analysis.detectors.volatility.bb_detector.BBSignalDetector"
            }
            class_path = detector_class_mapping.get(detector_name)
            if not class_path:
                logger.warning(f"Unknown technical detector: {detector_name}")
                return None
            
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            detector_class = getattr(module, class_name)
            return detector_class(detector_config.get("weight", 0.0))
                
        except Exception as e:
            logger.error(f"Failed to create technical detector {detector_name}: {e}")
            return None
    
    def initialize(self) -> bool:
        """전략 초기화"""
        try:
            self.orchestrator = self._create_orchestrator()
            self.is_initialized = True
            logger.info(f"DynamicCompositeStrategy '{self.strategy_name}' initialized with {len(self.technical_detectors)} detectors.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DynamicCompositeStrategy '{self.strategy_name}': {e}")
            return False
    
    def analyze(self, 
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Dict = None) -> StrategyResult:
        """
        동적 전략 분석 실행
        
        Args:
            df_with_indicators: 기술적 지표가 포함된 가격 데이터
            ticker: 종목 코드
            market_trend: 시장 추세
            long_term_trend: 장기 추세
            daily_extra_indicators: 거시 지표 데이터
            
        Returns:
            StrategyResult: 분석 결과
        """
        if not self.is_initialized:
            logger.error(f"Strategy '{self.strategy_name}' not initialized")
            return self._create_error_result("Strategy not initialized")
        
        try:
            # 1. DecisionContext 생성
            context = DecisionContext(self.strategy_config)
            context.ticker = ticker
            context.market_data = daily_extra_indicators or {}
            
            context.log_decision("ANALYSIS_START", f"Starting analysis for {ticker}")
            
            # 2. 기술적 지표 점수 계산
            self._calculate_technical_scores(context, df_with_indicators)
            
            # 3. 모디파이어 적용 (daily_extra_indicators는 이미 완결된 데이터로 간주)
            if self.modifier_engine:
                applied_count = self.modifier_engine.apply_all(context, df_with_indicators, daily_extra_indicators or {})
                logger.debug(f"Applied {applied_count} modifiers for {ticker}")
            
            # 4. 최종 점수 계산
            context.calculate_final_score()
            
            # 5. 신호 생성
            result = self._create_strategy_result(context, ticker, df_with_indicators, market_trend, long_term_trend)
            
            # 컨텍스트 저장 (디버깅용)
            self.last_context = context
            
            return result
            
        except Exception as e:
            logger.error(f"Error in dynamic strategy analysis for {ticker}: {e}", exc_info=True)
            return self._create_error_result(f"Analysis error: {e}")
    
    def _calculate_technical_scores(self, context: DecisionContext, df_with_indicators: pd.DataFrame):
        """기술적 지표 점수 계산"""
        context.log_decision("TECHNICAL_ANALYSIS_START", "Calculating technical indicator scores")
        
        for detector_name, detector in self.technical_detectors.items():
            try:
                # detector에서 점수 획득 (buy_score, sell_score, buy_details, sell_details)
                detector_result = detector.detect_signals(df_with_indicators)
                
                # detector 결과를 점수로 변환 (-100 ~ +100 범위)
                score = self._convert_detector_result_to_score(detector_result, detector_name)
                context.set_detector_score(detector_name, score)
                
            except Exception as e:
                logger.error(f"Error calculating score for {detector_name}: {e}")
                context.set_detector_score(detector_name, 0.0)
    
    def _convert_detector_result_to_score(self, detector_result: tuple, detector_name: str) -> float:
        """기존 detector의 결과를 점수로 변환"""
        try:
            buy_score, sell_score, buy_details, sell_details = detector_result
            
            # 매수/매도 점수를 -100~+100 범위로 정규화
            raw_score = buy_score - sell_score
            
            # 일반적인 detector 점수 범위를 고려한 정규화 (보통 0~5 범위)
            normalized_score = max(-100.0, min(100.0, raw_score * 20))  # 5점 -> 100점으로 스케일링
            
            return normalized_score
            
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Error converting detector result to score for {detector_name}: {e}")
            return 0.0
    
    
    
    def _create_strategy_result(self, context: DecisionContext, ticker: str,
                              df_with_indicators: pd.DataFrame,
                              market_trend: TrendType,
                              long_term_trend: TrendType) -> StrategyResult:
        """전략 결과 생성"""
        signal_type = context.get_signal_type()

        # 신호가 있는 경우 TradingSignal 생성
        trading_signal = None
        if signal_type != SignalType.NEUTRAL:
            current_price = df_with_indicators['Close'].iloc[-1]
            now_utc = pd.Timestamp.utcnow()

            # 1. 기술적 지표 근거 생성
            technical_evidences = []
            for detector_name, score in context.detector_raw_scores.items():
                if abs(score) > 0:
                    weight = context.current_weights.get(detector_name, 0.0)
                    technical_evidences.append(TechnicalIndicatorEvidence(
                        indicator_name=detector_name,
                        current_value=score,
                        condition_met=f"Normalized score of {score:.2f}",
                        contribution_score=score * weight
                    ))

            # 2. 시장 상황 근거 생성
            market_context_evidence = MarketContextEvidence(
                market_trend=market_trend.name,
                volatility_level=context.market_data.get('vix_level'),
                volume_analysis=None
            )

            # 3. 종합 신호 근거 (SignalEvidence) 생성
            applied_filters = [
                f"{m.modifier_name}: {m.reason}" for m in context.modifier_applications
                if m.applied and m.modifier_type == 'FILTER'
            ]
            score_adjustments = [
                f"{m.modifier_name}: {m.reason}" for m in context.modifier_applications
                if m.applied and m.modifier_type != 'FILTER'
            ]

            evidence = SignalEvidence(
                signal_timestamp=now_utc.to_pydatetime(),
                ticker=ticker,
                signal_type=signal_type.name,
                final_score=int(context.final_score),
                technical_evidences=technical_evidences,
                market_context_evidence=market_context_evidence,
                raw_signals=[f"{name}: {score:.2f}" for name, score in context.detector_raw_scores.items()],
                applied_filters=applied_filters,
                score_adjustments=score_adjustments
            )

            # 상세 로그를 안전하게 처리하여 리스트 생성
            detailed_log_messages = []
            for log in context.get_detailed_log():
                if isinstance(log, dict) and 'message' in log:
                    detailed_log_messages.append(str(log['action']))
                else:
                    detailed_log_messages.append(str(log))

            # 4. 최종 TradingSignal 생성
            trading_signal = TradingSignal(
                ticker=ticker,
                signal_type=signal_type,
                signal_score=int(context.final_score),
                timestamp_utc=now_utc.to_pydatetime(),
                current_price=current_price,
                market_trend=market_trend,
                long_term_trend=long_term_trend,
                details=detailed_log_messages,
                evidence=evidence
            )

        # StrategyResult 생성
        # 위에서 생성한 안전한 로그 리스트를 재사용
        signals_detected = detailed_log_messages if 'detailed_log_messages' in locals() else []
        if not signals_detected and trading_signal:
            signals_detected.append(f"Final Signal: {trading_signal.signal_type.name} with score {trading_signal.signal_score}")

        result = StrategyResult(
            strategy_name=self.strategy_name,
            strategy_type=self._get_strategy_type(),
            has_signal=(signal_type != SignalType.NEUTRAL),
            total_score=context.final_score,
            signal_strength=context.get_signal_strength(),
            signals_detected=signals_detected,
            signal=trading_signal,
            confidence=context.get_confidence(),
            buy_score=max(0.0, context.final_score),
            sell_score=max(0.0, -context.final_score)
        )

        return result
    
    def _create_error_result(self, error_message: str) -> StrategyResult:
        """에러 결과 생성"""
        return StrategyResult(
            strategy_name=self.strategy_name,
            strategy_type=self._get_strategy_type(),
            has_signal=False,
            total_score=0.0,
            signal_strength="WEAK",
            signals_detected=[f"ERROR: {error_message}"],
            signal=None,
            confidence=0.0,
            buy_score=0.0,
            sell_score=0.0
        )
    
    def get_last_decision_context(self) -> Optional[DecisionContext]:
        """마지막 분석의 DecisionContext 반환 (디버깅용)"""
        return self.last_context
    
    def get_context_summary(self) -> Optional[Dict[str, Any]]:
        """마지막 컨텍스트 요약 반환"""
        if self.last_context:
            return self.last_context.get_summary()
        return None
    
    def get_detailed_log(self) -> List[Dict[str, Any]]:
        """상세 분석 로그 반환"""
        if self.last_context:
            return self.last_context.get_detailed_log()
        return []