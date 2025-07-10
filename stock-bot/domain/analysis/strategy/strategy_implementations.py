"""
통합 전략 구현체 (정적/동적 전략 모두 지원)

모든 전략을 통합 관리하며, 확장성과 유지보수성을 고려한 설계
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_strategy import BaseStrategy, StrategyResult
from domain.analysis.config.static_strategies import StrategyType, StrategyConfig, get_strategy_config
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.stock.service.market_data_service import MarketDataService
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class AdaptiveMomentumStrategy(BaseStrategy):
    """
    적응형 모멘텀 전략: 추세와 모멘텀 전략을 결합하여 신호를 생성합니다.
    """
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        # StrategyFactory를 사용하여 내부적으로 다른 전략들을 인스턴스화
        self.trend_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_FOLLOWING)
        self.momentum_strategy = StrategyFactory.create_static_strategy(StrategyType.MOMENTUM)

    def initialize(self) -> bool:
        """하위 전략들을 초기화합니다."""
        is_trend_ok = self.trend_strategy.initialize()
        is_momentum_ok = self.momentum_strategy.initialize()
        self.is_initialized = is_trend_ok and is_momentum_ok
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        # 이 전략은 오케스트레이터를 직접 사용하지 않으므로 빈 것을 반환
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType, long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        # 1. 각 내부 전략으로부터 신호 분석
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")
        
        trend_result = self.trend_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)
        momentum_result = self.momentum_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)

        # 2. 신호 점수 조합 (가중치: 추세 50%, 모멘텀 50%)
        buy_score = (trend_result.buy_score * 0.5) + (momentum_result.buy_score * 0.5)
        sell_score = (trend_result.sell_score * 0.5) + (momentum_result.sell_score * 0.5)

        # 3. 최종 결과 생성
        final_signals = trend_result.signals_detected + momentum_result.signals_detected
        
        # 두 전략의 정지 손절 가격 중 더 보수적인(안전한) 값을 선택
        stop_loss_price = None
        if trend_result.stop_loss_price and momentum_result.stop_loss_price:
            if buy_score > sell_score: # 매수 신호일 경우 더 낮은 값
                stop_loss_price = min(trend_result.stop_loss_price, momentum_result.stop_loss_price)
            else: # 매도 신호일 경우 더 높은 값
                stop_loss_price = max(trend_result.stop_loss_price, momentum_result.stop_loss_price)
        elif trend_result.stop_loss_price:
            stop_loss_price = trend_result.stop_loss_price
        else:
            stop_loss_price = momentum_result.stop_loss_price

        # 4. StrategyResult 객체 직접 생성 (오류 수정)
        has_signal = buy_score > self.config.signal_threshold or sell_score > self.config.signal_threshold
        total_score = 0
        if has_signal:
            total_score = buy_score if buy_score > sell_score else sell_score

        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=has_signal,
            total_score=total_score,
            buy_score=buy_score,
            sell_score=sell_score,
            signals_detected=final_signals,
            stop_loss_price=stop_loss_price,
            signal_strength="", # dataclass에서 자동 계산
            signal=None # 필요 시 생성 로직 추가
        )


class ConservativeReversionHybridStrategy(BaseStrategy):
    """
    보수적 평균 회귀 하이브리드 전략:
    - CONSERVATIVE 전략으로 큰 추세를 확인합니다.
    - MEAN_REVERSION 전략으로 추세 내의 진입 시점을 포착합니다.
    """
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.conservative_strategy = StrategyFactory.create_static_strategy(StrategyType.CONSERVATIVE)
        self.mean_reversion_strategy = StrategyFactory.create_static_strategy(StrategyType.MEAN_REVERSION)

    def initialize(self) -> bool:
        is_conservative_ok = self.conservative_strategy.initialize()
        is_reversion_ok = self.mean_reversion_strategy.initialize()
        self.is_initialized = is_conservative_ok and is_reversion_ok
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType, long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        conservative_result = self.conservative_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)
        reversion_result = self.mean_reversion_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)

        buy_score = reversion_result.buy_score
        sell_score = reversion_result.sell_score

        # "추세 확인 후 진입" 로직
        # 1. 평균 회귀가 매수 신호를 보냈을 때
        if reversion_result.buy_score > reversion_result.sell_score:
            # 보수적 전략도 상승 추세에 동의하면 보너스 점수
            if conservative_result.buy_score > conservative_result.sell_score:
                buy_score += conservative_result.buy_score * 0.5  # 추세 점수의 50%를 보너스로
            # 추세가 반대이면 페널티
            else:
                buy_score *= 0.5
        
        # 2. 평균 회귀가 매도 신호를 보냈을 때
        elif reversion_result.sell_score > reversion_result.buy_score:
            # 보수적 전략도 하락 추세에 동의하면 보너스 점수
            if conservative_result.sell_score > conservative_result.buy_score:
                sell_score += conservative_result.sell_score * 0.5
            # 추세가 반대이면 페널티
            else:
                sell_score *= 0.5

        final_signals = conservative_result.signals_detected + reversion_result.signals_detected
        stop_loss_price = reversion_result.stop_loss_price

        has_signal = buy_score > self.config.signal_threshold or sell_score > self.config.signal_threshold
        total_score = max(buy_score, sell_score) if has_signal else 0

        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=has_signal,
            total_score=total_score,
            buy_score=buy_score,
            sell_score=sell_score,
            signals_detected=final_signals,
            stop_loss_price=stop_loss_price,
            signal_strength="",
            signal=None
        )


class MarketRegimeHybridStrategy(BaseStrategy):
    """
    시장 체제 적응형 하이브리드 전략:
    시장의 추세와 변동성을 진단하여, 최적의 하위 전략을 동적으로 선택합니다.
    """
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.trend_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_FOLLOWING)
        self.reversion_strategy = StrategyFactory.create_static_strategy(StrategyType.MEAN_REVERSION)
        self.volatility_strategy = StrategyFactory.create_static_strategy(StrategyType.VOLATILITY_BREAKOUT)
        self.market_data_service = MarketDataService()

    def initialize(self) -> bool:
        self.is_initialized = all([
            self.trend_strategy.initialize(),
            self.reversion_strategy.initialize(),
            self.volatility_strategy.initialize()
        ])
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType, long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        # 1. 시장 체제 진단
        current_date = df_with_indicators.index[-1].date()
        vix_value = self.market_data_service.get_vix_by_date(current_date) or 20 # VIX 데이터 없으면 중간값 사용
        
        is_trending = market_trend != TrendType.NEUTRAL
        is_volatile = vix_value > 25

        # 2. 최적의 하위 전략 선택
        chosen_strategy = None
        if is_trending and not is_volatile: # 안정적 상승장/하락장
            chosen_strategy = self.trend_strategy
        elif is_trending and is_volatile: # 변동성 상승장/하락장
            chosen_strategy = self.volatility_strategy
        elif not is_trending and is_volatile: # 추세 없는 변동성장 (하락장의 기술적 반등)
            chosen_strategy = self.reversion_strategy
        else: # 횡보장 (거래 없음)
            return StrategyResult(strategy_name=self.get_name(), strategy_type=self.strategy_type, has_signal=False, total_score=0, buy_score=0, sell_score=0, signals_detected=[], stop_loss_price=None, signal_strength="", signal=None)

        # 3. 선택된 전략으로 분석 실행
        result = chosen_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)
        
        # 4. 동적 리스크 관리 (VIX에 따라 점수 조정)
        if vix_value > 30: # 매우 위험
            result.buy_score *= 0.7
            result.sell_score *= 0.7
        elif vix_value < 15: # 매우 안정
            result.buy_score *= 1.2
            result.sell_score *= 1.2
            
        return result


class StableValueHybridStrategy(BaseStrategy):
    """
    안정 가치 하이브리드 전략:
    - CONSERVATIVE 전략으로 시장의 안정적인 상승 추세를 확인합니다.
    - TREND_PULLBACK 전략으로 추세 내의 눌림목 매수 시점을 포착합니다.
    """
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.conservative_strategy = StrategyFactory.create_static_strategy(StrategyType.CONSERVATIVE)
        self.pullback_strategy = StrategyFactory.create_static_strategy(StrategyType.TREND_PULLBACK)

    def initialize(self) -> bool:
        self.is_initialized = all([
            self.conservative_strategy.initialize(),
            self.pullback_strategy.initialize()
        ])
        return self.is_initialized

    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        return SignalDetectionOrchestrator()

    def analyze(self, df_with_indicators: pd.DataFrame, ticker: str, market_trend: TrendType, long_term_trend: TrendType, daily_extra_indicators: Dict) -> StrategyResult:
        if not self.is_initialized:
            raise RuntimeError(f"{self.get_name()}이 초기화되지 않았습니다.")

        conservative_result = self.conservative_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)
        pullback_result = self.pullback_strategy.analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)

        buy_score = 0
        sell_score = 0 # 이 전략은 매수만 고려

        # CONSERVATIVE 전략이 안정적인 상승 추세라고 판단할 때만,
        # TREND_PULLBACK의 눌림목 매수 신호를 채택
        if conservative_result.buy_score > conservative_result.sell_score:
            buy_score = pullback_result.buy_score

        final_signals = conservative_result.signals_detected + pullback_result.signals_detected
        stop_loss_price = pullback_result.stop_loss_price

        has_signal = buy_score > self.config.signal_threshold
        total_score = buy_score if has_signal else 0

        return StrategyResult(
            strategy_name=self.get_name(),
            strategy_type=self.strategy_type,
            has_signal=has_signal,
            total_score=total_score,
            buy_score=buy_score,
            sell_score=sell_score,
            signals_detected=final_signals,
            stop_loss_price=stop_loss_price,
            signal_strength="",
            signal=None
        )


class UniversalStrategy(BaseStrategy):
    """범용 전략 - 모든 정적 전략 타입을 지원하는 통합 클래스"""
    
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.strategy_type = strategy_type
        self.market_data_service = MarketDataService()  # MarketDataService 인스턴스 생성
        
    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략 설정에 따른 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 탐지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType, df_with_indicators: pd.DataFrame) -> float:
        """전략별 점수 조정 (전략 타입에 따라 다른 로직 적용)"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend, df_with_indicators)
        
        # 전략별 특화 로직
        if self.strategy_type == StrategyType.CONSERVATIVE:
            # 보수적 전략: 더 높은 임계값 요구
            adjusted_score *= 0.8
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 0.6
                
        elif self.strategy_type == StrategyType.AGGRESSIVE:
            # 공격적 전략: 더 낮은 임계값 허용
            adjusted_score *= 1.2
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.3
                
        elif self.strategy_type == StrategyType.MOMENTUM:
            # 모멘텀 전략: 추세 방향성 강화
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.15
            elif market_trend == TrendType.BEARISH:
                adjusted_score *= 0.9
                
        elif self.strategy_type == StrategyType.CONTRARIAN:
            # 역추세 전략: 추세와 반대 방향 강화
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 1.2  # 하락장에서 매수 신호 강화
            elif market_trend == TrendType.BULLISH:
                adjusted_score *= 0.8  # 상승장에서 매수 신호 약화
                
        elif self.strategy_type in [StrategyType.TREND_FOLLOWING, StrategyType.TREND_PULLBACK]:
            # 추세 기반 전략들: 추세 방향 확인 필요
            if market_trend == long_term_trend:
                adjusted_score *= 1.1  # 단기/장기 추세 일치 시 강화
            else:
                adjusted_score *= 0.9  # 추세 불일치 시 약화
                
        elif self.strategy_type == StrategyType.SCALPING:
            # 스캘핑 전략: 변동성이 높을 때 활성화
            current_date = df_with_indicators.index[-1].date()
            vix_value = self.market_data_service.get_vix_by_date(current_date)
            
            if vix_value is not None:
                if vix_value > 25:  # VIX가 25를 초과하면 변동성이 높다고 판단
                    adjusted_score *= 1.2  # 점수 20% 가산
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) > 25. Score adjusted by 1.2x.")
                elif vix_value < 15: # VIX가 15 미만이면 변동성이 낮다고 판단
                    adjusted_score *= 0.8 # 점수 20% 감산
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) < 15. Score adjusted by 0.8x.")
            else:
                logger.warning(f"SCALPING: VIX data not available for {current_date}. No adjustment made.")

        elif self.strategy_type in [StrategyType.MEAN_REVERSION, StrategyType.SWING]:
            # 평균 회귀/스윙 전략: 횡보장에서 유리
            if market_trend == TrendType.NEUTRAL:
                adjusted_score *= 1.15
                
        # 다중 시간대와 거시지표 기반 전략은 기본 로직 사용
        
        return adjusted_score


class UniversalStrategy(BaseStrategy):
    """범용 전략 - 모든 정적 전략 타입을 지원하는 통합 클래스"""
    
    def __init__(self, strategy_type: StrategyType, config: StrategyConfig):
        super().__init__(strategy_type, config)
        self.strategy_type = strategy_type
        self.market_data_service = MarketDataService()  # MarketDataService 인스턴스 생성
        
    def _get_strategy_type(self) -> StrategyType:
        return self.strategy_type
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략 설정에 따른 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 ��지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType, df_with_indicators: pd.DataFrame) -> float:
        """전략별 점수 조정 (전략 타입에 따라 다른 로직 적용)"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend, df_with_indicators)
        
        # 전략별 특화 로직
        if self.strategy_type == StrategyType.CONSERVATIVE:
            # 보수적 전략: 더 높은 임계값 요구
            adjusted_score *= 0.8
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 0.6
                
        elif self.strategy_type == StrategyType.AGGRESSIVE:
            # 공격적 전략: 더 낮은 임계값 허용
            adjusted_score *= 1.2
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.3
                
        elif self.strategy_type == StrategyType.MOMENTUM:
            # 모멘텀 전략: 추세 방향성 강화
            if market_trend == TrendType.BULLISH:
                adjusted_score *= 1.15
            elif market_trend == TrendType.BEARISH:
                adjusted_score *= 0.9
                
        elif self.strategy_type == StrategyType.CONTRARIAN:
            # 역추세 전략: 추세와 반대 방향 강화
            if market_trend == TrendType.BEARISH:
                adjusted_score *= 1.2  # 하락장에서 매수 신호 강화
            elif market_trend == TrendType.BULLISH:
                adjusted_score *= 0.8  # 상승장에서 매수 신호 약화
                
        elif self.strategy_type in [StrategyType.TREND_FOLLOWING, StrategyType.TREND_PULLBACK]:
            # 추세 기반 전략들: 추세 방향 확인 필요
            if market_trend == long_term_trend:
                adjusted_score *= 1.1  # 단기/장기 추세 일치 시 강화
            else:
                adjusted_score *= 0.9  # 추세 불일치 시 약화
                
        elif self.strategy_type == StrategyType.SCALPING:
            # 스캘핑 전략: 변동성이 높을 때 활성화
            current_date = df_with_indicators.index[-1].date()
            vix_value = self.market_data_service.get_vix_by_date(current_date)
            
            if vix_value is not None:
                if vix_value > 25:  # VIX��� 25를 초과하면 변동성이 높다고 판단
                    adjusted_score *= 1.2  # 점수 20% 가산
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) > 25. Score adjusted by 1.2x.")
                elif vix_value < 15: # VIX가 15 미만이면 변동성이 낮다고 판단
                    adjusted_score *= 0.8 # 점수 20% 감산
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) < 15. Score adjusted by 0.8x.")
            else:
                logger.warning(f"SCALPING: VIX data not available for {current_date}. No adjustment made.")

        elif self.strategy_type in [StrategyType.MEAN_REVERSION, StrategyType.SWING]:
            # 평균 회귀/스윙 전략: 횡보장에서 유리
            if market_trend == TrendType.NEUTRAL:
                adjusted_score *= 1.15
                
        # 다중 시간대와 거시지표 기반 전략은 기본 로직 사용
        
        return adjusted_score



class StrategyFactory:
    """
    통합 전략 팩토리 - 모든 정적 전략과 동적 전략 지원
    
    개선 사항:
    1. 모든 확장된 정적 전략 지원
    2. 동적 전략 생성 기능 추가
    3. 중복 경고 메시지 제거
    4. 설정 기반 전략 생성
    """
    
    @classmethod
    def create_static_strategy(cls, strategy_type: StrategyType, config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """정적 전략 인스턴스 생성"""
        if config is None:
            config = get_strategy_config(strategy_type)
            
        if config is None:
            logger.error(f"전략 설정을 찾을 수 없습니다: {strategy_type.value}")
            return None
            
        try:
            if strategy_type == StrategyType.ADAPTIVE_MOMENTUM:
                return AdaptiveMomentumStrategy(strategy_type, config)
            if strategy_type == StrategyType.CONSERVATIVE_REVERSION_HYBRID:
                return ConservativeReversionHybridStrategy(strategy_type, config)
            if strategy_type == StrategyType.MARKET_REGIME_HYBRID:
                return MarketRegimeHybridStrategy(strategy_type, config)
            if strategy_type == StrategyType.STABLE_VALUE_HYBRID:
                return StableValueHybridStrategy(strategy_type, config)
            
            # 모든 나머지 정적 전략을 UniversalStrategy로 생성
            strategy = UniversalStrategy(strategy_type, config)
            logger.info(f"정적 전략 생성 성공: {strategy_type.value}")
            return strategy
            
        except Exception as e:
            logger.error(f"정적 전략 생성 실패 {strategy_type.value}: {e}")
            return None
    
    @classmethod
    def create_dynamic_strategy(cls, strategy_name: str) -> Optional[BaseStrategy]:
        """동적 전략 인스턴스 생성"""
        try:
            from .dynamic_strategy import DynamicCompositeStrategy
            strategy = DynamicCompositeStrategy(strategy_name)
            logger.info(f"동적 전략 생성 성공: {strategy_name}")
            return strategy
            
        except Exception as e:
            logger.error(f"동적 전략 생성 실패 {strategy_name}: {e}")
            return None
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """전략 인스턴스 생성 (하위 호환성 유지)"""
        return cls.create_static_strategy(strategy_type, config)
    
    @classmethod
    def get_available_static_strategies(self) -> list[StrategyType]:
        """사용 가능한 정적 전략 목록 반환"""
        from domain.analysis.config.static_strategies import get_static_strategy_types
        return get_static_strategy_types()
    
    @classmethod
    def get_available_dynamic_strategies(self) -> list[str]:
        """사용 가능한 동적 전략 목록 반환"""
        try:
            from domain.analysis.config.dynamic_strategies import get_all_strategies
            return list(get_all_strategies().keys())
        except ImportError:
            return []
    
    @classmethod
    def is_strategy_supported(cls, strategy_identifier: str) -> tuple[bool, str]:
        """전략 지원 여부 확인"""
        # 정적 전략 확인
        try:
            strategy_type = StrategyType(strategy_identifier.lower())
            if get_strategy_config(strategy_type) is not None:
                return True, "static"
        except ValueError:
            pass
        
        # 동적 전략 확인
        try:
            from domain.analysis.config.dynamic_strategies import get_strategy_definition
            if get_strategy_definition(strategy_identifier) is not None:
                return True, "dynamic"
        except ImportError:
            def get_strategy_definition(name):
                return None
            if get_strategy_definition(strategy_identifier) is not None:
                return True, "dynamic"
        
        return False, "none"
    
    @classmethod
    def create_multiple_strategies(cls, strategy_configs: Dict[StrategyType, StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """여러 정적 전략 동시 생성"""
        strategies = {}
        for strategy_type, config in strategy_configs.items():
            strategy = cls.create_static_strategy(strategy_type, config)
            if strategy:
                strategies[strategy_type] = strategy
            else:
                logger.warning(f"전략 생성 실패로 건너뜀: {strategy_type.value}")
        return strategies 