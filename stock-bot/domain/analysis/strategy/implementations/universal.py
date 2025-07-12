import pandas as pd

from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.config.static_strategies import StrategyConfig, StrategyType
from domain.analysis.strategy.base_strategy import BaseStrategy
from domain.stock.service.market_data_service import MarketDataService
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


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

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType,
                                  df_with_indicators: pd.DataFrame) -> float:
        """전략별 점수 조정 (전략 타입에 따라 다른 로직 적용)"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend,
                                                           df_with_indicators)

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
                elif vix_value < 15:  # VIX가 15 미만이면 변동성이 낮다고 판단
                    adjusted_score *= 0.8  # 점수 20% 감산
                    logger.debug(f"SCALPING: VIX ({vix_value:.2f}) < 15. Score adjusted by 0.8x.")
            else:
                logger.warning(f"SCALPING: VIX data not available for {current_date}. No adjustment made.")

        elif self.strategy_type in [StrategyType.MEAN_REVERSION, StrategyType.SWING]:
            # 평균 회귀/스윙 전략: 횡보장에서 유리
            if market_trend == TrendType.NEUTRAL:
                adjusted_score *= 1.15

        # 다중 시간대와 거시지표 기반 전략은 기본 로직 사용

        return adjusted_score
