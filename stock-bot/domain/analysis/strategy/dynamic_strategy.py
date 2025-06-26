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
from .modifiers import ModifierEngine, ModifierFactory
from domain.analysis.config.dynamic_strategies import (
    get_strategy_definition, get_all_modifiers, MACRO_DETECTOR_MAPPING
)
from domain.analysis.models.trading_signal import TradingSignal, SignalType
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class DynamicCompositeStrategy(BaseStrategy):
    """
    동적 가중치 조절 전략
    
    이 전략은 다음과 같은 과정으로 동작합니다:
    1. DecisionContext 생성 (기본 가중치 설정)
    2. 각 기술적 지표 detector의 점수 계산
    3. 거시 지표 데이터 수집
    4. Modifier들을 우선순위 순으로 적용 (가중치 조정, 점수 보정, 거부 등)
    5. 최종 점수 계산 및 신호 생성
    """
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.strategy_config = get_strategy_definition(strategy_name)
        
        if not self.strategy_config:
            raise ValueError(f"Strategy definition not found: {strategy_name}")
        
        # BaseStrategy 초기화를 위한 더미 config 생성
        from domain.analysis.config.static_strategies import StrategyConfig, DetectorConfig, StrategyType
        
        # 동적 전략용 더미 config
        dummy_config = StrategyConfig(
            name=self.strategy_name,
            description=self.strategy_config["description"],
            signal_threshold=self.strategy_config.get("signal_threshold", 8.0),
            risk_per_trade=self.strategy_config.get("risk_per_trade", 0.02),
            detectors=[]  # 동적으로 관리하므로 빈 리스트
        )
        
        super().__init__(StrategyType.MACRO_DRIVEN, dummy_config)
        
        # 동적 전략 전용 속성
        self.technical_detectors: Dict[str, Any] = {}
        self.modifier_engine: Optional[ModifierEngine] = None
        self.last_context: Optional[DecisionContext] = None
        
    def _get_strategy_type(self) -> 'StrategyType':
        from domain.analysis.config.static_strategies import StrategyType
        return StrategyType.MACRO_DRIVEN
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """기술적 지표 detector들을 위한 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 전략 설정에서 기술적 지표 detector들을 동적으로 생성
        for detector_name, detector_config in self.strategy_config["detectors"].items():
            detector = self._create_technical_detector(detector_name, detector_config)
            if detector:
                orchestrator.add_detector(detector)
                self.technical_detectors[detector_name] = detector
        
        return orchestrator
    
    def _create_technical_detector(self, detector_name: str, detector_config: Dict[str, Any]):
        """기술적 지표 detector 생성"""
        try:
            # detector 클래스 매핑
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
            
            # 모듈과 클래스 분리
            module_path, class_name = class_path.rsplit('.', 1)
            
            # 모듈 동적 임포트
            module = importlib.import_module(module_path)
            detector_class = getattr(module, class_name)
            
            # detector 인스턴스 생성 (기본 가중치는 0으로 설정, 나중에 동적으로 조정)
            weight = detector_config.get("weight", 0.0)
            return detector_class(weight)
                
        except Exception as e:
            logger.error(f"Failed to create technical detector {detector_name}: {e}")
            return None
    
    def initialize(self) -> bool:
        """전략 초기화"""
        try:
            # 기술적 지표 오케스트레이터 초기화
            self.orchestrator = self._create_orchestrator()
            
            # 모디파이어 엔진 초기화
            modifier_definitions = get_all_modifiers()
            modifier_names = self.strategy_config.get("modifiers", [])
            
            modifiers = ModifierFactory.create_modifiers_from_config(
                modifier_names, modifier_definitions
            )
            self.modifier_engine = ModifierEngine(modifiers)
            
            self.is_initialized = True
            logger.info(f"DynamicCompositeStrategy '{self.strategy_name}' initialized with {len(modifiers)} modifiers")
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
            
            # 3. 거시 지표 데이터 준비
            market_data = self._prepare_market_data(daily_extra_indicators)
            
            # 4. 모디파이어 적용
            if self.modifier_engine:
                applied_count = self.modifier_engine.apply_all(context, df_with_indicators, market_data)
                logger.debug(f"Applied {applied_count} modifiers for {ticker}")
            
            # 5. 최종 점수 계산
            context.calculate_final_score()
            
            # 6. 신호 생성
            result = self._create_strategy_result(context, ticker, df_with_indicators)
            
            # 컨텍스트 저장 (디버깅용)
            self.last_context = context
            
            return result
            
        except Exception as e:
            logger.error(f"Error in dynamic strategy analysis for {ticker}: {e}")
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
    
    def _prepare_market_data(self, daily_extra_indicators: Optional[Dict]) -> Dict[str, Any]:
        """거시 지표 데이터 준비"""
        if not daily_extra_indicators:
            return {}
        
        market_data = {}
        
        # 거시 지표 데이터를 모디파이어가 이해할 수 있는 형태로 변환
        macro_mapping = {
            "VIX": "vix",
            "FEAR_GREED_INDEX": "fear_greed_index", 
            "DXY": "dxy",
            "US_10Y_TREASURY_YIELD": "us_10y_treasury_yield",
            "BUFFETT_INDICATOR": "buffett_indicator",
            "PUT_CALL_RATIO": "put_call_ratio",
            "SP500_INDEX": "sp500_sma_200"  # S&P 500 지수
        }
        
        for db_key, modifier_key in macro_mapping.items():
            if db_key in daily_extra_indicators:
                market_data[modifier_key] = daily_extra_indicators[db_key]
                
                # S&P 500의 경우 200일선 정보도 추가 (임시로 현재가의 95%로 설정)
                if modifier_key == "sp500_sma_200":
                    market_data[f"{modifier_key}_reference"] = daily_extra_indicators[db_key] * 0.95
        
        return market_data
    
    def _create_strategy_result(self, context: DecisionContext, ticker: str, 
                              df_with_indicators: pd.DataFrame) -> StrategyResult:
        """전략 결과 생성"""
        signal_type = context.get_signal_type()
        
        # 신호가 있는 경우 TradingSignal 생성
        trading_signal = None
        if signal_type != SignalType.NEUTRAL:
            current_price = df_with_indicators['close'].iloc[-1]
            
            trading_signal = TradingSignal(
                ticker=ticker,
                signal_type=signal_type,
                strength=context.get_signal_strength(),
                confidence=context.get_confidence(),
                price=current_price,
                timestamp=pd.Timestamp.now(),
                strategy_name=self.strategy_name,
                technical_indicators=context.detector_raw_scores,
                market_conditions={
                    "final_score": context.final_score,
                    "threshold": context.current_threshold,
                    "modifiers_applied": len([m for m in context.modifier_applications if m.applied]),
                    "veto_status": context.is_vetoed
                }
            )
        
        # StrategyResult 생성
        signals_detected = []
        for modifier_app in context.modifier_applications:
            if modifier_app.applied:
                signals_detected.append(f"{modifier_app.modifier_name}: {modifier_app.reason}")
        
        # 기술적 지표 신호도 추가
        for detector_name, score in context.detector_raw_scores.items():
            if abs(score) > 5:  # 임계값 이상인 경우만
                direction = "BUY" if score > 0 else "SELL"
                signals_detected.append(f"{detector_name}: {direction} ({score:.1f})")
        
        result = StrategyResult(
            strategy_name=self.strategy_name,
            strategy_type=self._get_strategy_type(),
            has_signal=(signal_type != SignalType.NEUTRAL),
            total_score=context.final_score,
            signal_strength=context.get_signal_strength(),
            signals_detected=signals_detected,
            signal=trading_signal,
            confidence=context.get_confidence(),
            buy_score=max(0, context.final_score),
            sell_score=max(0, -context.final_score)
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