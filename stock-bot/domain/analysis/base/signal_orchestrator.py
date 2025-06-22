from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .signal_detector import SignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_THRESHOLD
from domain.analysis.models.trading_signal import (
    SignalEvidence, 
    TechnicalIndicatorEvidence,
    MultiTimeframeEvidence,
    MarketContextEvidence,
    RiskManagementEvidence
)

logger = get_logger(__name__)


class SignalDetectionOrchestrator:
    """여러 신호 감지기를 조율하여 최종 신호를 생성하는 오케스트레이터"""
    
    def __init__(self):
        self.detectors: List[SignalDetector] = []
        self.signal_threshold = SIGNAL_THRESHOLD
    
    def add_detector(self, detector: SignalDetector):
        """감지기를 추가합니다."""
        self.detectors.append(detector)
        logger.debug(f"Added detector: {detector.name}")
    
    def remove_detector(self, detector_name: str):
        """감지기를 제거합니다."""
        self.detectors = [d for d in self.detectors if d.name != detector_name]
        logger.debug(f"Removed detector: {detector_name}")
    
    def detect_signals(self, 
                      df: pd.DataFrame,
                      ticker: str,
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Dict:
        """
        모든 감지기를 사용하여 신호를 감지합니다.
        
        Args:
            df: OHLCV 및 지표 데이터
            ticker: 주식 티커
            market_trend: 시장 추세
            long_term_trend: 장기 추세
            daily_extra_indicators: 일봉 추가 지표
            
        Returns:
            Dict: 감지된 신호 정보 또는 빈 딕셔너리
        """
        if df.empty or len(df) < 2:
            logger.warning(f"Not enough data for signal detection for {ticker}.")
            return {}
        
        total_buy_score = 0
        total_sell_score = 0
        all_buy_details = []
        all_sell_details = []
        
        # 각 감지기로부터 신호 수집
        for detector in self.detectors:
            try:
                buy_score, sell_score, buy_details, sell_details = detector.detect_signals(
                    df, market_trend, long_term_trend, daily_extra_indicators
                )
                
                total_buy_score += buy_score
                total_sell_score += sell_score
                all_buy_details.extend(buy_details)
                all_sell_details.extend(sell_details)
                
            except Exception as e:
                logger.error(f"Error in detector {detector.name}: {e}", exc_info=True)
                continue
        
        # 근거 수집
        all_technical_evidences = self._collect_all_technical_evidences()
        
        # 최종 신호 판단
        return self._evaluate_final_signal(
            ticker, total_buy_score, total_sell_score, 
            all_buy_details, all_sell_details, 
            market_trend, long_term_trend, df,
            daily_extra_indicators, all_technical_evidences
        )
    
    def _evaluate_final_signal(self, 
                              ticker: str,
                              buy_score: float, 
                              sell_score: float,
                              buy_details: List[str], 
                              sell_details: List[str],
                              market_trend: TrendType,
                              long_term_trend: TrendType,
                              df: pd.DataFrame,
                              daily_extra_indicators: Dict = None,
                              all_technical_evidences: List[TechnicalIndicatorEvidence] = None) -> Dict:
        """최종 신호를 평가하고 결과를 반환합니다."""
        
        # 시장 추세에 따른 임계값 조정
        adjusted_threshold = self._get_adjusted_threshold(market_trend)
        
        strong_buy_signal = buy_score >= adjusted_threshold and buy_score > sell_score
        strong_sell_signal = sell_score >= adjusted_threshold and sell_score > buy_score
        
        latest_data = df.iloc[-1]
        
        if strong_buy_signal and long_term_trend == TrendType.BULLISH:
            logger.info(f"BUY SIGNAL CONFIRMED for {ticker} (Score: {buy_score:.2f})")
            
            stop_loss_price = self._calculate_stop_loss(df, 'buy')
            
            # 상세 근거 생성
            evidence = self._create_signal_evidence(
                'BUY', ticker, int(buy_score), latest_data.name.to_pydatetime(),
                all_technical_evidences, daily_extra_indicators, 
                market_trend, long_term_trend, stop_loss_price, latest_data['Close']
            )
            
            return {
                'type': 'BUY',
                'score': int(buy_score),
                'details': buy_details,
                'current_price': latest_data['Close'],
                'timestamp': latest_data.name.to_pydatetime(),
                'stop_loss_price': stop_loss_price,
                'evidence': evidence
            }
            
        elif strong_sell_signal and long_term_trend == TrendType.BEARISH:
            logger.info(f"SELL SIGNAL CONFIRMED for {ticker} (Score: {sell_score:.2f})")
            
            stop_loss_price = self._calculate_stop_loss(df, 'sell')
            
            # 상세 근거 생성
            evidence = self._create_signal_evidence(
                'SELL', ticker, int(sell_score), latest_data.name.to_pydatetime(),
                all_technical_evidences, daily_extra_indicators, 
                market_trend, long_term_trend, stop_loss_price, latest_data['Close']
            )
            
            return {
                'type': 'SELL',
                'score': int(sell_score),
                'details': sell_details,
                'current_price': latest_data['Close'],
                'timestamp': latest_data.name.to_pydatetime(),
                'stop_loss_price': stop_loss_price,
                'evidence': evidence
            }
        
        return {}
    
    def _get_adjusted_threshold(self, market_trend: TrendType) -> float:
        """시장 추세에 따른 임계값을 조정합니다."""
        if market_trend == TrendType.BEARISH:
            return self.signal_threshold * 1.2
        elif market_trend == TrendType.BULLISH:
            return self.signal_threshold * 0.8
        return self.signal_threshold
    
    def _calculate_stop_loss(self, df: pd.DataFrame, signal_type: str) -> Optional[float]:
        """ATR 기반 손절매 가격을 계산합니다."""
        try:
            latest_data = df.iloc[-1]
            
            # ATR 컬럼 찾기
            atr_col = next((col for col in df.columns if col.startswith('ATR_')), None)
            if not atr_col:
                return None
            
            current_atr = latest_data.get(atr_col, 0.0)
            if pd.isna(current_atr) or current_atr <= 0:
                return None
            
            if signal_type == 'buy':
                stop_loss = latest_data['Close'] - (current_atr * 2)
                return max(stop_loss, 0.01)  # 음수 방지
            else:  # sell
                return latest_data['Close'] + (current_atr * 2)
                
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return None
    
    def _collect_all_technical_evidences(self) -> List[TechnicalIndicatorEvidence]:
        """모든 감지기로부터 기술적 지표 근거를 수집합니다."""
        all_evidences = []
        
        for detector in self.detectors:
            # 각 감지기가 get_technical_evidences 메서드를 구현했는지 확인
            if hasattr(detector, 'get_technical_evidences'):
                try:
                    evidences = detector.get_technical_evidences()
                    all_evidences.extend(evidences)
                except Exception as e:
                    logger.error(f"Error collecting evidences from {detector.name}: {e}")
        
        return all_evidences
    
    def _create_signal_evidence(self, 
                               signal_type: str,
                               ticker: str,
                               score: int,
                               timestamp: datetime,
                               technical_evidences: List[TechnicalIndicatorEvidence],
                               daily_extra_indicators: Dict,
                               market_trend: TrendType,
                               long_term_trend: TrendType,
                               stop_loss_price: Optional[float],
                               current_price: float) -> SignalEvidence:
        """종합적인 신호 근거를 생성합니다."""
        
        try:
            # 다중 시간대 근거 생성
            multi_timeframe_evidence = None
            if daily_extra_indicators and daily_extra_indicators.get('multi_timeframe_analysis'):
                mta = daily_extra_indicators['multi_timeframe_analysis']
                
                # 일봉 지표 추출
                daily_indicators = {}
                if daily_extra_indicators.get('daily_data') is not None:
                    daily_df = daily_extra_indicators['daily_data']
                    if not daily_df.empty:
                        latest_daily = daily_df.iloc[-1]
                        for col in ['Close', 'SMA_20', 'SMA_50', 'RSI_14', 'ADX_14']:
                            if col in latest_daily.index:
                                daily_indicators[col] = float(latest_daily[col])
                
                # 시간봉 지표는 technical_evidences에서 추출
                hourly_indicators = {}
                for evidence in technical_evidences:
                    if evidence.timeframe == '1h':
                        hourly_indicators[evidence.indicator_name] = evidence.current_value
                
                multi_timeframe_evidence = MultiTimeframeEvidence(
                    daily_trend=mta.get('daily_trend', 'NEUTRAL'),
                    hourly_trend=mta.get('hourly_trend', 'NEUTRAL'),
                    consensus=mta.get('consensus', 'NEUTRAL'),
                    daily_indicators=daily_indicators,
                    hourly_indicators=hourly_indicators,
                    confidence_adjustment=1.0  # 기본값
                )
            
            # 시장 상황 근거 생성
            market_context_evidence = MarketContextEvidence(
                market_trend=market_trend.value,
                volatility_level=self._assess_volatility_level(technical_evidences)
            )
            
            # 리스크 관리 근거 생성
            risk_management_evidence = None
            if stop_loss_price:
                stop_loss_percentage = abs((current_price - stop_loss_price) / current_price * 100)
                risk_management_evidence = RiskManagementEvidence(
                    stop_loss_method="ATR_2x",
                    stop_loss_percentage=stop_loss_percentage,
                    risk_reward_ratio=self._calculate_risk_reward_ratio(
                        current_price, stop_loss_price, signal_type
                    )
                )
            
            # 최종 SignalEvidence 생성
            evidence = SignalEvidence(
                signal_timestamp=timestamp,
                ticker=ticker,
                signal_type=signal_type,
                final_score=score,
                technical_evidences=technical_evidences or [],
                multi_timeframe_evidence=multi_timeframe_evidence,
                market_context_evidence=market_context_evidence,
                risk_management_evidence=risk_management_evidence,
                raw_signals=[f"{detector.name}: contributed to {signal_type} signal" for detector in self.detectors],
                applied_filters=["market_trend_filter", "long_term_trend_filter"],
                score_adjustments=[f"Market trend adjustment: {market_trend.value}"]
            )
            
            return evidence
            
        except Exception as e:
            logger.error(f"Error creating signal evidence: {e}")
            # 기본 근거 반환
            return SignalEvidence(
                signal_timestamp=timestamp,
                ticker=ticker,
                signal_type=signal_type,
                final_score=score
            )
    
    def _assess_volatility_level(self, technical_evidences: List[TechnicalIndicatorEvidence]) -> str:
        """기술적 지표를 기반으로 변동성 수준을 평가합니다."""
        try:
            # ATR 기반 변동성 평가
            atr_evidence = next((e for e in technical_evidences if 'ATR' in e.indicator_name), None)
            if atr_evidence:
                atr_value = atr_evidence.current_value
                # 간단한 변동성 분류 (실제로는 더 정교한 로직 필요)
                if atr_value > 5.0:
                    return "HIGH"
                elif atr_value > 2.0:
                    return "MEDIUM"
                else:
                    return "LOW"
            return "UNKNOWN"
        except Exception:
            return "UNKNOWN"
    
    def _calculate_risk_reward_ratio(self, current_price: float, stop_loss_price: float, signal_type: str) -> float:
        """위험 대비 수익 비율을 계산합니다."""
        try:
            if signal_type == 'BUY':
                # 매수: 목표가를 현재가의 110%로 가정
                target_price = current_price * 1.1
                reward = target_price - current_price
                risk = current_price - stop_loss_price
            else:
                # 매도: 목표가를 현재가의 90%로 가정
                target_price = current_price * 0.9
                reward = current_price - target_price
                risk = stop_loss_price - current_price
            
            return reward / risk if risk > 0 else 0.0
        except Exception:
            return 0.0 