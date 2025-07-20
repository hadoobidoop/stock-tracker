from typing import Dict, Optional

import pandas as pd

from domain.signals.config.signals.service.signal_processor import SignalProcessor
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.detectors.momentum.rsi_detector import RSISignalDetector
from domain.signals.detectors.trend_following.adx_detector import ADXSignalDetector
from domain.signals.models.enums import StrategyType
from domain.signals.models.strategy_result import StrategyResult
from domain.strategies.base import BaseStrategy
from domain.strategies.single.swing.configs.swing_config import SWING_STRATEGY_CONFIG
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)

class SwingStrategy(BaseStrategy):
    """
    Swing(스윙) 전략 - 중기 추세 변화를 포착하는 트레이딩 전략 (중앙 Detector + 파라미터 주입)

    [설계 의도]
    - 중앙 Detector(SMA, MACD, RSI, ADX) + 파라미터 주입 방식
    - Detector별 가중치, 임계값, 포지션 관리 등은 SWING_STRATEGY_CONFIG 상수(dict)로 관리
    - 모든 Detector는 중앙 detector를 사용하여 일관성 있게 관리
    - 신호 분석, 점수 조정, 근거 수집, 쿨다운, 예외처리 등 robust하게 구현

    [활용 포인트]
    - 중기(수일~수주) 추세 전환/반전 구간에서 진입/청산 신호 포착
    - Detector별 상세 근거 기록, 전략별 파라미터 튜닝 용이
    - 유지보수/확장/테스트가 독립적으로 가능
    """
    def __init__(self, strategy_type: StrategyType, config: dict = None):
        """
        SwingStrategy 생성자
        Args:
            strategy_type (StrategyType): 전략 Enum (보통 StrategyType.SWING)
            config (dict, optional): 전략 파라미터 dict. 미지정 시 SWING_STRATEGY_CONFIG 사용
        주요 파라미터:
            - detector_weights: 각 Detector별 가중치
            - signal_threshold: 신호 발생 임계값
            - position_management: 포지션 개수/보유기간 등
        """
        config = config or SWING_STRATEGY_CONFIG
        super().__init__(strategy_type, config)
        self.config = config
        self.orchestrator: Optional[SignalProcessor] = None

    def initialize(self) -> bool:
        """
        Swing 전략의 중앙 Detector 조합 및 orchestrator 초기화
        - 중앙 Detector(SMASignalDetector, MACDSignalDetector, RSISignalDetector, ADXSignalDetector) 사용
        - 파라미터 주입: 전략별 특화 설정 적용
        - 각 Detector의 가중치는 config['detector_weights']에서 관리
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            # Swing 전략용 파라미터 설정
            swing_sma_params = {
                'adx_threshold': 20,  # 기본 20 유지
                'continuation_weight': 0.5,  # 기본 0.4에서 더 보수적으로
                'trend_confirmation_required': True  # 추세 확인 필요
            }
            
            swing_macd_params = {
                'signal_sensitivity': 1.0,  # 기본 1.0 유지
                'trend_confirmation_required': True  # 추세 확인 필요
            }
            
            swing_rsi_params = {
                'oversold_threshold': 35,  # 기본 35 유지
                'overbought_threshold': 65,  # 기본 65 유지
                'trend_confirmation_required': True  # 추세 확인 필요
            }
            
            swing_adx_params = {
                'adx_threshold': 25,  # 기본 25 유지
                'trend_strength_required': True  # 추세 강도 확인 필요
            }
            
            detectors = [
                SMASignalDetector(
                    weight=self.config['detector_weights']['sma'],
                    name="Swing_SMA_Detector",
                    parameters=swing_sma_params
                ),
                MACDSignalDetector(
                    weight=self.config['detector_weights']['macd'],
                    name="Swing_MACD_Detector",
                    parameters=swing_macd_params
                ),
                RSISignalDetector(
                    weight=self.config['detector_weights']['rsi'],
                    name="Swing_RSI_Detector",
                    parameters=swing_rsi_params
                ),
                ADXSignalDetector(
                    weight=self.config['detector_weights']['adx'],
                    name="Swing_ADX_Detector",
                    parameters=swing_adx_params
                )
            ]
            self.orchestrator = SignalProcessor()
            for detector in detectors:
                self.orchestrator.add_detector(detector)
            self.is_initialized = True
            logger.info(f"{self.get_name()} 초기화 완료 (중앙 Detector + 파라미터 주입)")
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
        Args:
            df_with_indicators (pd.DataFrame): 기술적 지표 포함 데이터프레임 (최신 캔들 기준)
            ticker (str): 종목 코드
            market_trend (TrendType): 단기 시장 추세 (BULLISH/BEARISH/NEUTRAL)
            long_term_trend (TrendType): 장기 시장 추세 (BULLISH/BEARISH/NEUTRAL)
            daily_extra_indicators (dict, optional): 추가 지표
        Returns:
            StrategyResult: 신호 발생 여부, 점수, 근거, 매수/매도 점수 등
        내부 동작:
            - 쿨다운 체크(중복 신호 방지), orchestrator 기반 신호/점수/근거 수집
            - market_trend==NEUTRAL 시 점수 1.15배(스윙 특화)
            - 장기추세(BULLISH/BEARISH) 가중치 buy/sell에 적용
            - 신호 근거, 점수, buy/sell score, stop_loss 등 StrategyResult에 기록
            - 예외 발생 시 안전하게 실패 반환
        """
        if not self.is_initialized or not self.orchestrator:
            raise RuntimeError(f"{self.get_name()}이(가) 초기화되지 않았습니다.")

        self.last_analysis_time = pd.Timestamp.now(tz='UTC')

        try:
            signal_result = self.orchestrator.detect_signals(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators or {}
            )

            has_signal = bool(signal_result and signal_result.get('type'))
            score = signal_result.get('score', 0)

            # Swing 특화 점수 조정: 시장 중립(NEUTRAL) 시 점수 1.15배
            if market_trend == TrendType.NEUTRAL:
                score *= 1.15

            # 성능 지표 업데이트 (최근 100개 평균)
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

            # === 장기추세 가중치 적용 ===
            buy_score = signal_result.get('buy_score', 0.0)
            sell_score = signal_result.get('sell_score', 0.0)
            if long_term_trend == TrendType.BULLISH:
                buy_score *= 1.2
            elif long_term_trend == TrendType.BEARISH:
                sell_score *= 1.2
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