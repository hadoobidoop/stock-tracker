from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from infrastructure.db.models.enums import TrendType
from domain.analysis.config.strategy_settings import StrategyConfig, StrategyType, DetectorConfig
from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
from domain.analysis.strategy.base_strategy import BaseStrategy, StrategyResult
from infrastructure.logging import get_logger

"""
구체적인 전략 구현체들

각 전략은 BaseStrategy를 상속받아 고유한 신호 감지 로직을 구현합니다.
"""

class ConservativeStrategy(BaseStrategy):
    """보수적 전략 - 높은 신뢰도의 강한 신호만 사용"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.CONSERVATIVE
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """보수적 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 감지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """보수적 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 보수적 전략은 더 높은 임계값 요구
        adjusted_score *= 0.8
        
        # 하락장에서는 매수 신호 억제
        if market_trend == TrendType.BEARISH:
            adjusted_score *= 0.6
            
        return adjusted_score


class BalancedStrategy(BaseStrategy):
    """균형잡힌 전략 - 다양한 신호를 균형있게 사용"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.BALANCED
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """균형잡힌 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """균형잡힌 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 다양한 신호의 균형을 확인
        signal_types = set(signal.split('_')[0].lower() for signal in self.orchestrator.last_signals)
        if len(signal_types) >= 3:  # 3가지 이상의 서로 다른 신호 유형이 있으면 가중
            adjusted_score *= 1.2
        
        return adjusted_score


class AggressiveStrategy(BaseStrategy):
    """공격적 전략 - 더 많은 거래 기회 포착"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.AGGRESSIVE
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """공격적 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """공격적 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 공격적 전략은 더 낮은 임계값 허용
        adjusted_score *= 1.2
        
        # 상승장에서는 매수 신호 강화
        if market_trend == TrendType.BULLISH:
            adjusted_score *= 1.3
            
        return adjusted_score


class MomentumStrategy(BaseStrategy):
    """모멘텀 전략 - RSI와 스토캐스틱 지표 기반"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """모멘텀 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """모멘텀 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        orchestrator = self._create_orchestrator()
        if orchestrator.last_signals:
            # RSI나 Stochastic 신호가 있으면 가중치 부여
            momentum_signals = [s for s in orchestrator.last_signals if any(x in s.lower() for x in ['rsi', 'stoch'])]
            if momentum_signals:
                adjusted_score *= 1.2
                
            # 과매수/과매도 상태에서는 반대 방향 신호 강화
            overbought_signals = [s for s in orchestrator.last_signals if 'overbought' in s.lower()]
            oversold_signals = [s for s in orchestrator.last_signals if 'oversold' in s.lower()]
            if overbought_signals:
                adjusted_score *= 1.3  # 매도 신호 강화
            elif oversold_signals:
                adjusted_score *= 1.3  # 매수 신호 강화
            
        return adjusted_score


class TrendFollowingStrategy(BaseStrategy):
    """추세 추종 전략 - SMA, MACD, ADX 지표 기반"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.TREND_FOLLOWING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """추세 추종 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """추세 추종 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 추세가 강할 때 추가 가중치
        if market_trend == long_term_trend and market_trend != TrendType.NEUTRAL:
            adjusted_score *= 1.3
            
        orchestrator = self._create_orchestrator()
        if orchestrator.last_signals:
            # ADX 신호가 있으면 추가 가중치
            adx_signals = [s for s in orchestrator.last_signals if 'adx' in s.lower()]
            if adx_signals:
                adjusted_score *= 1.1
                
            # 추세 일치 여부 확인
            trend_signals = [s for s in orchestrator.last_signals if any(x in s.lower() for x in ['sma', 'macd'])]
            if len(trend_signals) >= 2:  # 2개 이상의 추세 지표가 일치하면 가중
                adjusted_score *= 1.2
            
        return adjusted_score


class ContrarianStrategy(BaseStrategy):
    """역추세 전략 - 과매수/과매도 조건에서 반전 매매"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.CONTRARIAN
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """역추세 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """역추세 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 추세와 반대 방향으로 거래할 때 가중치
        if market_trend != TrendType.NEUTRAL:
            adjusted_score *= 1.2
            
        orchestrator = self._create_orchestrator()
        if orchestrator.last_signals:
            # RSI나 Stochastic 과매수/과매도 신호가 있으면 가중치
            overbought_oversold = [s for s in orchestrator.last_signals if any(x in s.lower() for x in ['overbought', 'oversold'])]
            if overbought_oversold:
                adjusted_score *= 1.3
                
            # 추세 반전 신호가 있으면 추가 가중치
            reversal_signals = [s for s in orchestrator.last_signals if 'reversal' in s.lower()]
            if reversal_signals:
                adjusted_score *= 1.2
            
        return adjusted_score


class ScalpingStrategy(BaseStrategy):
    """스캘핑 전략 - 빠른 진입과 청산"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.SCALPING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """스캘핑 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """스캘핑 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 변동성이 높을 때 추가 가중치
        if market_trend != TrendType.NEUTRAL:
            adjusted_score *= 1.2
            
        orchestrator = self._create_orchestrator()
        if orchestrator.last_signals:
            # 거래량이 높을 때 추가 가중치
            volume_signals = [s for s in orchestrator.last_signals if 'volume' in s.lower()]
            if volume_signals:
                adjusted_score *= 1.1
            
        return adjusted_score


class SwingStrategy(BaseStrategy):
    """스윙 전략 - 다일 홀딩, 높은 임계값"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.SWING
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """스윙 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # 설정에서 감지기들을 동적으로 생성
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """스윙 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # 장기 추세와 일치할 때 가중치
        if market_trend == long_term_trend and market_trend != TrendType.NEUTRAL:
            adjusted_score *= 1.3
            
        # 변동성이 낮을 때 선호
        if market_trend == TrendType.NEUTRAL:
            adjusted_score *= 1.1
            
        # 장기 신호가 있으면 추가 가중치
        orchestrator = self._create_orchestrator()
        if orchestrator.last_signals:
            long_term_signals = [s for s in orchestrator.last_signals if any(x in s.lower() for x in ['daily', 'weekly', 'long'])]
            if long_term_signals:
                adjusted_score *= 1.2
            
        return adjusted_score


class VixFearGreedStrategy(BaseStrategy):
    """VIX 기반 공포&탐욕 전략 - 시장 심리를 반영한 역발상 투자"""
    
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.VIX_FEAR_GREED
    
    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """VIX 전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        
        # dict config 처리
        if isinstance(self.config, dict):
            detectors_config = self.config.get("detectors", [])
            for detector_info in detectors_config:
                detector_class_name = detector_info["detector_class"]
                weight = detector_info["weight"]
                enabled = detector_info.get("enabled", True)
                
                if not enabled:
                    continue
                
                # 감지기 생성 (간단화)
                if detector_class_name == "SMASignalDetector":
                    from domain.analysis.detectors.trend_following.sma_detector import SMASignalDetector
                    orchestrator.add_detector(SMASignalDetector(weight))
                elif detector_class_name == "MACDSignalDetector":
                    from domain.analysis.detectors.trend_following.macd_detector import MACDSignalDetector
                    orchestrator.add_detector(MACDSignalDetector(weight))
                elif detector_class_name == "RSISignalDetector":
                    from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
                    orchestrator.add_detector(RSISignalDetector(weight))
                elif detector_class_name == "VolumeSignalDetector":
                    from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
                    orchestrator.add_detector(VolumeSignalDetector(weight))
        else:
            # StrategyConfig의 경우 기존 방식 사용
            for detector_config in self.config.detectors:
                detector = self._create_detector_instance(detector_config)
                if detector:
                    orchestrator.add_detector(detector)
        
        return orchestrator
    
    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        """VIX 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        # VIX 분석 수행
        try:
            from domain.analysis.utils.market_indicators import MarketIndicatorAnalyzer
            analyzer = MarketIndicatorAnalyzer()
            market_analysis = analyzer.get_combined_market_sentiment()
            
            if market_analysis:
                vix_analysis = market_analysis.get('vix_analysis', {})
                combined_signal = market_analysis.get('combined_signal', {})
                market_sentiment = market_analysis.get('market_sentiment', 'NEUTRAL')
                
                # VIX 기반 점수 조정 (조건 완화)
                fear_level = vix_analysis.get('fear_level', 'MODERATE_FEAR')
                vix_signal = vix_analysis.get('trading_signal', {})
                current_vix = vix_analysis.get('current_vix', 20)
                
                logger.info(f"VIX 전략 디버그 - VIX: {current_vix}, 공포레벨: {fear_level}, 기본점수: {base_score}")
                
                # 조건을 더 관대하게 수정
                if fear_level == 'EXTREME_FEAR':
                    adjusted_score *= 2.0  # 100% 증가
                    logger.info(f"VIX 극도 공포 상태: 매수 신호 강화 (VIX: {current_vix})")
                    
                elif fear_level == 'HIGH_FEAR':
                    adjusted_score *= 1.7  # 70% 증가
                    logger.info(f"VIX 높은 공포 상태: 매수 신호 강화 (VIX: {current_vix})")
                    
                elif fear_level == 'MODERATE_FEAR' and current_vix > 25:  # 새로 추가: 보통 공포도 25 이상이면 기회
                    adjusted_score *= 1.3  # 30% 증가
                    logger.info(f"VIX 보통 공포 상태 (25+): 매수 신호 적용 (VIX: {current_vix})")
                    
                elif fear_level == 'COMPLACENCY':
                    adjusted_score *= 0.6  # 40% 감소 (위험 신호)
                    logger.info(f"VIX 자만 상태: 매수 신호 억제 (VIX: {current_vix})")
                
                # VIX 트렌드 반영
                vix_trend = vix_analysis.get('trend', 'NEUTRAL')
                if vix_trend == 'RAPIDLY_RISING':
                    adjusted_score *= 1.3  # 급상승 시 기회
                elif vix_trend == 'RAPIDLY_FALLING' and fear_level in ['EXTREME_FEAR', 'HIGH_FEAR']:
                    adjusted_score *= 1.2  # 공포에서 회복 중
                
                # 시장 심리와 추세 일치성 확인
                if market_sentiment == 'FEARFUL' and market_trend == TrendType.BEARISH:
                    adjusted_score *= 1.4  # 공포와 하락 추세 일치 시 강화
                elif market_sentiment == 'GREEDY' and market_trend == TrendType.BULLISH:
                    adjusted_score *= 0.7  # 탐욕과 상승 추세 일치 시 주의
                
                # 결합된 신호 반영
                if combined_signal.get('type') == 'BUY':
                    adjusted_score *= (1 + combined_signal.get('confidence', 0) * 0.5)
                elif combined_signal.get('type') == 'SELL':
                    adjusted_score *= (1 - combined_signal.get('confidence', 0) * 0.3)
                
                logger.info(f"VIX 전략 최종 점수: {base_score} -> {adjusted_score}")
                
            else:
                logger.warning("VIX 시장 분석 데이터가 없음 - 기본 점수 사용")
                
        except Exception as e:
            logger.error(f"VIX 분석 실패: {e}")
            # VIX 분석 실패 시 기본 전략으로 동작
            adjusted_score *= 0.9
        
        return adjusted_score
    
    def analyze(self, 
                df_with_indicators: pd.DataFrame,
                ticker: str,
                market_trend: TrendType = TrendType.NEUTRAL,
                long_term_trend: TrendType = TrendType.NEUTRAL,
                daily_extra_indicators: Dict = None) -> StrategyResult:
        """VIX 전략의 신호 분석"""
        
        # VIX 분석을 daily_extra_indicators에 추가
        try:
            from domain.analysis.utils.market_indicators import get_market_indicator_analysis
            market_indicator_analysis = get_market_indicator_analysis()
            
            if daily_extra_indicators is None:
                daily_extra_indicators = {}
            
            daily_extra_indicators['market_indicator_analysis'] = market_indicator_analysis
            
        except Exception as e:
            logger.error(f"시장 지표 분석 추가 실패: {e}")
        
        # 부모 클래스의 분석 실행
        return super().analyze(df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators)

    def get_name(self):
        return self.config["name"] if isinstance(self.config, dict) else super().get_name()
    def get_description(self):
        return self.config["description"] if isinstance(self.config, dict) else super().get_description()


# ========================================
# --- 새로 추가된 5가지 전략 구현체 ---
# ========================================

class MeanReversionStrategy(BaseStrategy):
    """평균 회귀 전략"""
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        return orchestrator

class TrendPullbackStrategy(BaseStrategy):
    """추세 추종 눌림목 전략"""
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.TREND_PULLBACK

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        return orchestrator

class VolatilityBreakoutStrategy(BaseStrategy):
    """변동성 돌파 전략"""
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.VOLATILITY_BREAKOUT

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        return orchestrator

class QualityTrendStrategy(BaseStrategy):
    """고신뢰도 복합 추세 전략"""
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.QUALITY_TREND

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        return orchestrator

class MultiTimeframeStrategy(BaseStrategy):
    """다중 시간대 확인 전략"""
    def _get_strategy_type(self) -> StrategyType:
        return StrategyType.MULTI_TIMEFRAME

    def _create_orchestrator(self) -> SignalDetectionOrchestrator:
        """전략용 오케스트레이터 생성"""
        orchestrator = SignalDetectionOrchestrator()
        for detector_config in self.config.detectors:
            detector = self._create_detector_instance(detector_config)
            if detector:
                orchestrator.add_detector(detector)
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend: TrendType, long_term_trend: TrendType) -> float:
        # 이 전략은 daily_extra_indicators에 있는 필터링 결과에 크게 의존하므로,
        # 추가적인 점수 조정 로직이 필요하다면 여기에 구현할 수 있습니다.
        # 예를 들어, multi-timeframe 필터가 통과되었을 때 점수를 더 부여할 수 있습니다.
        return super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)


class AdxRsiVixStrategy(BaseStrategy):
    """
    ADX + RSI + VIX 조합 전략
    - 미시: ADX, RSI
    - 거시: VIX
    """
    def __init__(self, strategy_type, config):
        super().__init__(strategy_type, config)
        self.adx_threshold = self.config.get("adx_threshold", 15)
        self.rsi_buy = self.config.get("rsi_buy", 40)
        self.rsi_sell = self.config.get("rsi_sell", 60)
        self.vix_buy = self.config.get("vix_buy", 20)
        self.vix_sell = self.config.get("vix_sell", 12)
        self.macro_weight = self.config.get("macro_weight", 1.2)
        self.macro_penalty = self.config.get("macro_penalty", 0.7)

    def _get_strategy_type(self):
        return StrategyType.ADX_RSI_VIX

    def _create_orchestrator(self):
        # ADX, RSI만 사용하는 단순 오케스트레이터
        from domain.analysis.detectors.trend_following.adx_detector import ADXSignalDetector
        from domain.analysis.detectors.momentum.rsi_detector import RSISignalDetector
        from domain.analysis.base.signal_orchestrator import SignalDetectionOrchestrator
        orchestrator = SignalDetectionOrchestrator()
        orchestrator.add_detector(ADXSignalDetector(3.0))  # 기본 가중치
        orchestrator.add_detector(RSISignalDetector(3.0))  # 기본 가중치
        return orchestrator

    def _adjust_score_by_strategy(self, base_score: float, market_trend, long_term_trend) -> float:
        """ADX+RSI+VIX 전략의 점수 조정"""
        adjusted_score = super()._adjust_score_by_strategy(base_score, market_trend, long_term_trend)
        
        logger = get_logger(__name__)
        logger.info(f"ADX+RSI+VIX 전략 - 기본점수: {base_score}, 조정점수: {adjusted_score}")
        
        # VIX 기반 추가 조정
        try:
            from domain.analysis.utils.market_indicators import MarketIndicatorAnalyzer
            analyzer = MarketIndicatorAnalyzer()
            vix_analysis = analyzer.get_vix_analysis()
            vix = vix_analysis.get("current_vix", 20)
            fear_level = vix_analysis.get("fear_level", "MODERATE_FEAR")
            
            logger.info(f"ADX+RSI+VIX - VIX: {vix:.2f}, 공포레벨: {fear_level}")
            
            # VIX 기반 점수 조정
            if vix >= self.vix_buy:  # 공포 -> 매수 기회
                adjusted_score *= self.macro_weight
                logger.info(f"VIX 공포상태로 점수 강화: {vix:.2f} >= {self.vix_buy}")
            elif vix <= self.vix_sell:  # 안도 -> 매도/조심
                adjusted_score *= self.macro_penalty
                logger.info(f"VIX 안도상태로 점수 감소: {vix:.2f} <= {self.vix_sell}")
            else:
                logger.info(f"VIX 중립: {vix:.2f}")
            
        except Exception as e:
            logger.warning(f"VIX 분석 실패: {e}")
            adjusted_score *= 0.9  # 약간 감소
        
        logger.info(f"ADX+RSI+VIX 최종 점수: {base_score} -> {adjusted_score}")
        return adjusted_score

    def get_name(self):
        return self.config["name"] if isinstance(self.config, dict) else super().get_name()
    def get_description(self):
        return self.config["description"] if isinstance(self.config, dict) else super().get_description()


# 전략 팩토리 클래스
class StrategyFactory:
    """전략 팩토리 - 전략 타입에 따라 적절한 전략 인스턴스 생성"""
    
    _strategy_classes = {
        StrategyType.CONSERVATIVE: ConservativeStrategy,
        StrategyType.BALANCED: BalancedStrategy,
        StrategyType.AGGRESSIVE: AggressiveStrategy,
        StrategyType.MOMENTUM: MomentumStrategy,
        StrategyType.TREND_FOLLOWING: TrendFollowingStrategy,
        StrategyType.CONTRARIAN: ContrarianStrategy,
        StrategyType.SCALPING: ScalpingStrategy,
        StrategyType.SWING: SwingStrategy,
        StrategyType.MEAN_REVERSION: MeanReversionStrategy,
        StrategyType.TREND_PULLBACK: TrendPullbackStrategy,
        StrategyType.VOLATILITY_BREAKOUT: VolatilityBreakoutStrategy,
        StrategyType.QUALITY_TREND: QualityTrendStrategy,
        StrategyType.MULTI_TIMEFRAME: MultiTimeframeStrategy,
        StrategyType.VIX_FEAR_GREED: VixFearGreedStrategy,
        StrategyType.ADX_RSI_VIX: AdxRsiVixStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: StrategyConfig) -> BaseStrategy:
        """전략 인스턴스를 생성합니다."""
        strategy_class = cls._strategy_classes.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"지원하지 않는 전략 타입: {strategy_type}")
        
        try:
            return strategy_class(strategy_type, config)
        except Exception as e:
            raise RuntimeError(f"전략 생성 실패 {strategy_type}: {e}")
    
    @classmethod
    def get_available_strategies(cls) -> list[StrategyType]:
        """사용 가능한 전략 타입 목록을 반환합니다."""
        return list(cls._strategy_classes.keys())
    
    @classmethod
    def create_multiple_strategies(cls, strategy_configs: Dict[StrategyType, StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """여러 전략을 동시에 생성합니다."""
        strategies = {}
        for strategy_type, config in strategy_configs.items():
            try:
                strategies[strategy_type] = cls.create_strategy(strategy_type, config)
            except Exception as e:
                print(f"전략 생성 실패 {strategy_type}: {e}")
        
        return strategies 