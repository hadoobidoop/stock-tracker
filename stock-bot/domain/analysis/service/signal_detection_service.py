from typing import Dict, Optional, List, Any
from datetime import datetime
import pandas as pd

from infrastructure.db.models.enums import TrendType
from domain.analysis.config.strategy_settings import StrategyType, STRATEGY_CONFIGS
from domain.analysis.strategy.strategy_manager import StrategyManager
from domain.analysis.strategy.base_strategy import StrategyResult
from infrastructure.logging import get_logger

# 기존 호환성을 위한 import
from ..base.signal_orchestrator import SignalDetectionOrchestrator
from ..detectors.trend_following.sma_detector import SMASignalDetector
from ..detectors.trend_following.macd_detector import MACDSignalDetector
from ..detectors.momentum.rsi_detector import RSISignalDetector
from ..detectors.volume.volume_detector import VolumeSignalDetector
from ..detectors.composite.composite_detector import CompositeSignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_WEIGHTS

logger = get_logger(__name__)

class DetectorFactory:
    """
    신호 감지기 팩토리 클래스 (기존 호환성 유지)
    
    새로운 전략 시스템으로 마이그레이션하면서도 기존 코드와의 호환성을 유지합니다.
    """
    
    @staticmethod
    def create_trend_following_detectors() -> list:
        """추세 추종 감지기들 생성"""
        return [
            SMASignalDetector(SIGNAL_WEIGHTS["golden_cross_sma"]),
            MACDSignalDetector(SIGNAL_WEIGHTS["macd_cross"])
        ]
    
    @staticmethod
    def create_momentum_detectors() -> list:
        """모멘텀 감지기들 생성"""
        return [
            RSISignalDetector(SIGNAL_WEIGHTS["rsi_bounce_drop"])
        ]
    
    @staticmethod
    def create_volume_detectors() -> list:
        """거래량 감지기들 생성"""
        return [
            VolumeSignalDetector(SIGNAL_WEIGHTS["volume_surge"])
        ]
    
    @staticmethod
    def create_composite_detectors() -> list:
        """복합 감지기들 생성"""
        macd_detector = MACDSignalDetector(0)  # 가중치는 복합에서 설정
        volume_detector = VolumeSignalDetector(0)
        
        return [
            CompositeSignalDetector(
                detectors=[macd_detector, volume_detector],
                weight=SIGNAL_WEIGHTS["macd_volume_confirm"],
                require_all=True,
                name="MACD_Volume_Confirm"
            )
        ]
    
    @staticmethod
    def create_default_orchestrator(daily_extra_indicators: Dict = None) -> SignalDetectionOrchestrator:
        """기본 설정된 오케스트레이터 생성 (레거시 지원)"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 각 카테고리별 감지기 추가
        for detector in DetectorFactory.create_trend_following_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_momentum_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_volume_detectors():
            orchestrator.add_detector(detector)
        
        for detector in DetectorFactory.create_composite_detectors():
            orchestrator.add_detector(detector)
        
        return orchestrator
    
    @staticmethod
    def create_conservative_orchestrator() -> SignalDetectionOrchestrator:
        """보수적 전략용 오케스트레이터 (레거시 지원)"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 높은 신뢰도 감지기만 사용
        orchestrator.add_detector(SMASignalDetector(SIGNAL_WEIGHTS["golden_cross_sma"] * 1.5))
        orchestrator.add_detector(MACDSignalDetector(SIGNAL_WEIGHTS["macd_cross"] * 1.5))
        
        return orchestrator
    
    @staticmethod
    def create_aggressive_orchestrator() -> SignalDetectionOrchestrator:
        """공격적 전략용 오케스트레이터 (레거시 지원)"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 모든 감지기 사용 + 낮은 임계값
        for detector in DetectorFactory.create_trend_following_detectors():
            orchestrator.add_detector(detector)
        for detector in DetectorFactory.create_momentum_detectors():
            orchestrator.add_detector(detector)
        for detector in DetectorFactory.create_volume_detectors():
            orchestrator.add_detector(detector)
        
        return orchestrator


class EnhancedSignalDetectionService:
    """
    향상된 신호 감지 서비스 - 새로운 전략 시스템 기반
    
    특징:
    1. 여러 전략을 동적으로 교체 가능
    2. 전략 조합 및 앙상블 지원
    3. 자동 전략 선택
    4. 성능 모니터링
    5. 지표 프리컴퓨팅 및 캐시
    """
    
    def __init__(self):
        self.strategy_manager = StrategyManager()
        self.is_initialized = False
        
        # 지표 프리컴퓨팅 캐시
        self.precomputed_indicators: Dict[str, pd.DataFrame] = {}
        self.cache_last_updated: Dict[str, datetime] = {}
        self.cache_ttl_minutes = 5  # 5분 캐시 유효시간
        
    def initialize(self, strategy_types: List[StrategyType] = None) -> bool:
        """서비스 초기화"""
        logger.info("Enhanced Signal Detection Service 초기화 시작")
        
        try:
            # 전략 매니저 초기화
            success = self.strategy_manager.initialize_strategies(strategy_types)
            
            if success:
                self.is_initialized = True
                logger.info("Enhanced Signal Detection Service 초기화 완료")
                
                # 현재 활성화된 전략 정보 로깅
                current_info = self.strategy_manager.get_current_strategy_info()
                logger.info(f"현재 활성 전략: {current_info}")
                
                return True
            else:
                logger.error("전략 초기화 실패")
                return False
                
        except Exception as e:
            logger.error(f"서비스 초기화 실패: {e}")
            return False
    
    def detect_signals_with_strategy(self, 
                                   df_with_indicators: pd.DataFrame,
                                   ticker: str,
                                   strategy_type: StrategyType = None,
                                   market_trend: TrendType = TrendType.NEUTRAL,
                                   long_term_trend: TrendType = TrendType.NEUTRAL,
                                   daily_extra_indicators: Dict = None) -> StrategyResult:
        """
        지정된 전략으로 신호를 감지합니다.
        
        Args:
            df_with_indicators: 지표가 계산된 OHLCV 데이터
            ticker: 종목 코드
            strategy_type: 사용할 전략 (None이면 현재 활성 전략)
            market_trend: 시장 추세
            long_term_trend: 장기 추세
            daily_extra_indicators: 일봉 추가 지표
            
        Returns:
            StrategyResult: 전략 실행 결과
        """
        if not self.is_initialized:
            raise RuntimeError("서비스가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        
        # 지표 캐시 업데이트
        self._update_indicator_cache(ticker, df_with_indicators)
        
        # 전략 교체 (필요한 경우)
        if strategy_type and strategy_type != self.get_current_strategy_type():
            self.switch_strategy(strategy_type)
        
        # 신호 감지 실행
        result = self.strategy_manager.analyze_with_current_strategy(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        logger.debug(f"신호 감지 완료 [{ticker}]: {result.strategy_name}, Score: {result.total_score:.2f}")
        
        return result
    
    def analyze_all_strategies(self, 
                             df_with_indicators: pd.DataFrame,
                             ticker: str,
                             market_trend: TrendType = TrendType.NEUTRAL,
                             long_term_trend: TrendType = TrendType.NEUTRAL,
                             daily_extra_indicators: Dict = None) -> Dict[StrategyType, StrategyResult]:
        """모든 활성화된 전략으로 분석합니다."""
        if not self.is_initialized:
            raise RuntimeError("서비스가 초기화되지 않았습니다.")
        
        logger.info(f"모든 전략으로 신호 분석 시작 [{ticker}]")
        
        # 지표 캐시 업데이트
        self._update_indicator_cache(ticker, df_with_indicators)
        
        # 모든 전략으로 분석
        results = self.strategy_manager.analyze_with_all_strategies(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
        
        # 결과 요약 로깅
        signal_count = sum(1 for result in results.values() if result.has_signal)
        logger.info(f"전략 분석 완료 [{ticker}]: {signal_count}/{len(results)}개 전략에서 신호 생성")
        
        return results
    
    def analyze_with_current_strategy(self, 
                                    df_with_indicators: pd.DataFrame,
                                    ticker: str,
                                    market_trend: TrendType = TrendType.NEUTRAL,
                                    long_term_trend: TrendType = TrendType.NEUTRAL,
                                    daily_extra_indicators: Dict = None) -> StrategyResult:
        """현재 활성화된 전략으로 분석합니다."""
        if not self.is_initialized:
            raise RuntimeError("서비스가 초기화되지 않았습니다.")
        
        # 지표 캐시 업데이트
        self._update_indicator_cache(ticker, df_with_indicators)
        
        # 현재 전략으로 분석
        return self.strategy_manager.analyze_with_current_strategy(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
    
    def switch_strategy(self, strategy_type: StrategyType) -> bool:
        """전략을 교체합니다."""
        if not self.is_initialized:
            logger.warning("서비스가 초기화되지 않았습니다.")
            return False
        
        return self.strategy_manager.switch_strategy(strategy_type)
    
    def set_strategy_mix(self, mix_name: str) -> bool:
        """전략 조합을 설정합니다."""
        if not self.is_initialized:
            logger.warning("서비스가 초기화되지 않았습니다.")
            return False
        
        return self.strategy_manager.set_strategy_mix(mix_name)
    
    def enable_auto_strategy_selection(self, enable: bool = True):
        """자동 전략 선택을 활성화/비활성화합니다."""
        if not self.is_initialized:
            logger.warning("서비스가 초기화되지 않았습니다.")
            return
        
        self.strategy_manager.enable_auto_strategy_selection(enable)
    
    def get_current_strategy_type(self) -> Optional[StrategyType]:
        """현재 활성화된 전략 타입을 반환합니다."""
        if not self.is_initialized:
            return None
        
        if self.strategy_manager.current_strategy:
            return self.strategy_manager.current_strategy.strategy_type
        return None
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """현재 전략 정보를 반환합니다."""
        if not self.is_initialized:
            return {"error": "서비스가 초기화되지 않았습니다."}
        
        return self.strategy_manager.get_current_strategy_info()
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """사용 가능한 전략 목록을 반환합니다."""
        if not self.is_initialized:
            return []
        
        return self.strategy_manager.get_available_strategies()
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """전략별 성능 요약을 반환합니다."""
        if not self.is_initialized:
            return {}
        
        return self.strategy_manager.get_strategy_performance_summary()
    
    def precompute_indicators_for_ticker(self, 
                                       ticker: str, 
                                       df: pd.DataFrame,
                                       force_update: bool = False) -> pd.DataFrame:
        """
        특정 종목의 지표를 미리 계산합니다.
        
        이는 사용자가 원하는 "최대한 많은 지표를 미리 계산해두기" 기능입니다.
        """
        cache_key = f"{ticker}_indicators"
        current_time = datetime.now()
        
        # 캐시 확인
        if not force_update and cache_key in self.precomputed_indicators:
            last_updated = self.cache_last_updated.get(cache_key)
            if last_updated and (current_time - last_updated).seconds < self.cache_ttl_minutes * 60:
                logger.debug(f"지표 캐시 히트: {ticker}")
                return self.precomputed_indicators[cache_key]
        
        # 지표 계산
        from domain.analysis.utils import calculate_all_indicators
        
        logger.info(f"지표 프리컴퓨팅 시작: {ticker}")
        df_with_indicators = calculate_all_indicators(df)
        
        # 캐시 저장
        self.precomputed_indicators[cache_key] = df_with_indicators
        self.cache_last_updated[cache_key] = current_time
        
        logger.debug(f"지표 프리컴퓨팅 완료: {ticker}, 지표 수: {len(df_with_indicators.columns)}")
        
        return df_with_indicators
    
    def _update_indicator_cache(self, ticker: str, df_with_indicators: pd.DataFrame):
        """지표 캐시를 업데이트합니다."""
        cache_key = f"{ticker}_indicators"
        self.precomputed_indicators[cache_key] = df_with_indicators
        self.cache_last_updated[cache_key] = datetime.now()
    
    def clear_indicator_cache(self, ticker: str = None):
        """지표 캐시를 삭제합니다."""
        if ticker:
            cache_key = f"{ticker}_indicators"
            self.precomputed_indicators.pop(cache_key, None)
            self.cache_last_updated.pop(cache_key, None)
            logger.info(f"지표 캐시 삭제: {ticker}")
        else:
            self.precomputed_indicators.clear()
            self.cache_last_updated.clear()
            logger.info("모든 지표 캐시 삭제")
    
    def save_strategy_configs(self, file_path: str):
        """전략 설정을 파일로 저장합니다."""
        if not self.is_initialized:
            logger.warning("서비스가 초기화되지 않았습니다.")
            return
        
        self.strategy_manager.save_strategies_to_file(file_path)
        logger.info(f"전략 설정 저장: {file_path}")
    
    def load_strategy_configs(self, file_path: str) -> bool:
        """파일에서 전략 설정을 로드합니다."""
        if not self.is_initialized:
            logger.warning("서비스가 초기화되지 않았습니다.")
            return False
        
        success = self.strategy_manager.load_strategies_from_file(file_path)
        if success:
            logger.info(f"전략 설정 로드: {file_path}")
        return success


# 기존 호환성을 위한 레거시 서비스 (기존 코드가 그대로 작동하도록)
class SignalDetectionService:
    """레거시 신호 감지 서비스 - 기존 코드 호환성"""
    
    def __init__(self):
        # 내부적으로 새로운 서비스 사용
        self._enhanced_service = EnhancedSignalDetectionService()
        self._orchestrator = None
        
    def initialize(self):
        """레거시 초기화"""
        success = self._enhanced_service.initialize([StrategyType.BALANCED])
        if success:
            self._orchestrator = DetectorFactory.create_default_orchestrator()
        return success
    
    def detect_signals(self, 
                      df_with_indicators: pd.DataFrame,
                      ticker: str,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Dict:
        """레거시 신호 감지 (기존 인터페이스 유지)"""
        
        # 새로운 서비스가 초기화되어 있으면 사용
        if self._enhanced_service.is_initialized:
            result = self._enhanced_service.detect_signals_with_strategy(
                df_with_indicators, ticker, StrategyType.BALANCED,
                market_trend, long_term_trend, daily_extra_indicators
            )
            
            # 기존 형태로 변환
            return {
                'score': result.total_score,
                'type': 'BUY' if result.has_signal else None,
                'details': result.signals_detected,
                'stop_loss_price': None,  # 필요시 구현
                'strategy_name': result.strategy_name
            }
        
        # 폴백: 기존 방식
        elif self._orchestrator:
            return self._orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )
        
        else:
            return None