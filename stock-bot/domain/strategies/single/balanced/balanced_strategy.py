from datetime import datetime
from typing import Dict, Optional, Any

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.detectors.composite.composite_detector import CompositeSignalDetector
# 중앙 Detector import
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector
from domain.signals.detectors.trend_following.adx_detector import ADXSignalDetector
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.signals.models.trading_signal import TradingSignal
from domain.strategies.base import BaseStrategy
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .configs.balanced_config import BalancedStrategyConfig

logger = get_logger(__name__)


class BalancedStrategy(BaseStrategy):
    """
    균형잡힌 거래 전략.
    중앙 Detector를 파라미터 주입 방식으로 사용하여 안정적이고 균형있는 신호 감지.
    """

    def __init__(self, strategy_type: StrategyType, config: BalancedStrategyConfig):
        super().__init__(strategy_type, config)
        self.orchestrator: Optional[SignalProcessor] = None
        self.config = config  # BalancedStrategyConfig로 타입 지정

    def initialize(self) -> bool:
        """
        Detector 조합 및 orchestrator 초기화
        - 중앙 Detector들을 파라미터 주입 방식으로 사용
        - Composite Detector: MACD+Volume 컨펌(신호 신뢰도 강화)
        - Detector별 가중치는 config.detector_weights에서 관리
        """
        try:
            # 균형잡힌 전략용 파라미터들 (기본값 유지하되 안정성 중심)
            balanced_sma_params = {
                'adx_threshold': 20,  # 기본값 유지
                'continuation_weight': 0.4,  # 기본값 유지 (안정성)
                'trend_confirmation_required': True  # 확인 필요
            }
            
            balanced_volume_params = {
                'volume_surge_factor': 1.5,  # 기본값 유지
                'trend_continuation_weight': 0.5,  # 기본값 유지
                'min_trend_days': 3  # 기본값 유지 (안정성)
            }
            
            balanced_rsi_params = {
                'oversold_threshold': 35,  # 기본값 유지
                'overbought_threshold': 70,  # 기본값 유지
                'exit_bonus_multiplier': 1.2  # 기본값 유지
            }
            
            # 중앙 Detector들을 파라미터와 함께 생성
            detectors = [
                SMASignalDetector(
                    weight=self.config.detector_weights['sma'],
                    name="Balanced_SMA_Detector",
                    parameters=balanced_sma_params
                ),
                MACDSignalDetector(weight=self.config.detector_weights['macd']),
                RSISignalDetector(
                    weight=self.config.detector_weights['rsi'],
                    name="Balanced_RSI_Detector",
                    parameters=balanced_rsi_params
                ),
                VolumeSignalDetector(
                    weight=self.config.detector_weights['volume'],
                    name="Balanced_Volume_Detector",
                    parameters=balanced_volume_params
                ),
                ADXSignalDetector(weight=self.config.detector_weights['adx']),
                CompositeSignalDetector(
                    detectors=[
                        MACDSignalDetector(weight=0),
                        VolumeSignalDetector(weight=0, parameters=balanced_volume_params)
                    ],
                    weight=self.config.detector_weights['composite'],
                    require_all=True,
                    name="Balanced_MACD_Volume_Confirm"
                )
            ]
            self.orchestrator = SignalProcessor()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (중앙 Detector 파라미터 주입 방식 사용)")
            return True
        except Exception as e:
            logger.error(f"{self.get_name()} 초기화 실패: {e}")
            self.is_initialized = False
            return False

    def analyze(self,
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Optional[Dict] = None) -> StrategyResult:
        """
        신호 분석 및 결과 반환
        - 쿨다운 체크, orchestrator 기반 신호/점수/근거 수집
        - score_multiplier(1.0)로 점수 조정 없음
        - 장기추세(BULLISH/BEARISH) 가중치 buy/sell에 적용
        - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
        - 예외 발생 시 안전하게 실패 반환
        """
        
        # 쿨다운 체크
        current_time = datetime.now()
        if not self.can_generate_signal(current_time):
            logger.debug(f"{self.get_name()} 쿨다운 중 - 신호 생성 스킵")
            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=False,
                total_score=0.0,
                signal_strength="WEAK",
                signals_detected=[],
            )
        
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")

        self.last_analysis_time = current_time

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

            # Balanced 특화 점수 조정 (점수 조정 없음)
            original_score = score
            score *= self.config.score_multiplier  # 1.0 (조정 없음)

            # 성능 지표 업데이트
            self.score_history.append(score)
            if len(self.score_history) > 100:
                self.score_history.pop(0)
            if self.score_history:
                self.average_score = sum(self.score_history) / len(self.score_history)

            trading_signal = None
            if has_signal:
                self.signals_generated += 1
                trading_signal = self._create_trading_signal(
                    signal_result, ticker, score, df_with_indicators
                )
                logger.info(f"{self.get_name()} 신호 생성: {signal_result.get('type')} (점수: {original_score:.2f} → {score:.2f})")

            # === 장기추세 가중치 적용 ===
            buy_score = signal_result.get('buy_score', 0.0)
            sell_score = signal_result.get('sell_score', 0.0)
            if long_term_trend == TrendType.BULLISH:
                buy_score *= self.config.long_term_bullish_multiplier
            elif long_term_trend == TrendType.BEARISH:
                sell_score *= self.config.long_term_bearish_multiplier
            # ============================

            return StrategyResult(
                strategy_name=self.get_name(),
                strategy_type=self.strategy_type,
                has_signal=has_signal,
                total_score=score,
                signal_strength="",
                signals_detected=signal_result.get('details', []),
                signal=trading_signal,
                buy_score=buy_score,
                sell_score=sell_score,
                stop_loss_price=signal_result.get('stop_loss_price')
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
            )

    def _create_trading_signal(self, signal_result: Dict, ticker: str, score: float,
                             df_with_indicators: pd.DataFrame) -> TradingSignal:
        """
        TradingSignal 객체 생성 (Balanced 전략 특화)
        - 신호 근거, 조정 내역, 필터 등 evidence 상세 기록
        - score_adjustments, applied_filters 등 전략별 설명 포함
        """
        from domain.signals.models.trading_signal import SignalEvidence, SignalType

        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL

        # Balanced 전략 특화 근거 수집
        evidence = SignalEvidence(
            signal_timestamp=datetime.now(),
            ticker=ticker,
            signal_type=signal_result.get('type', 'BUY'),
            final_score=int(score),
            raw_signals=signal_result.get('details', []),
            applied_filters=[
                f"Strategy: {self.get_name()}",
                f"Score Multiplier: {self.config.score_multiplier}",
                "Balanced approach - no aggressive adjustments"
            ],
            score_adjustments=[
                f"Strategy adjustment applied: {self.get_name()}",
                f"Original score: {signal_result.get('score', 0):.2f}",
                f"Adjusted score: {score:.2f}",
                "Balanced strategy - minimal score adjustments"
            ]
        )

        return TradingSignal(
            signal_id=None,
            ticker=ticker,
            signal_type=signal_type,
            signal_score=int(score),
            timestamp_utc=datetime.now(),
            current_price=df_with_indicators['Close'].iloc[-1],
            market_trend=TrendType(signal_result.get('market_trend', 'NEUTRAL')),
            long_term_trend=TrendType(signal_result.get('long_term_trend', 'NEUTRAL')),
            details=signal_result.get('details', []),
            stop_loss_price=signal_result.get('stop_loss_price'),
            evidence=evidence
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Balanced 전략 성능 지표 반환
        - 주요 파라미터, 가중치, 임계값 등 config 기반 정보 포함
        - 전략별 튜닝/비교/모니터링에 활용
        """
        base_metrics = super().get_performance_metrics()
        balanced_metrics = {
            'score_multiplier': self.config.score_multiplier,
            'signal_threshold': self.config.signal_threshold,
            'max_positions': self.config.max_positions,
            'position_hold_hours': self.config.position_hold_hours,
            'detector_weights': self.config.detector_weights,
            'strategy_approach': 'Balanced - minimal adjustments'
        }
        base_metrics.update(balanced_metrics)
        return base_metrics 