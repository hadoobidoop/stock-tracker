from typing import Dict, List, Optional
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from .signal_detector import SignalDetector
from domain.analysis.config.analysis_settings import SIGNAL_THRESHOLD

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
        
        # 최종 신호 판단
        return self._evaluate_final_signal(
            ticker, total_buy_score, total_sell_score, 
            all_buy_details, all_sell_details, 
            market_trend, long_term_trend, df
        )
    
    def _evaluate_final_signal(self, 
                              ticker: str,
                              buy_score: float, 
                              sell_score: float,
                              buy_details: List[str], 
                              sell_details: List[str],
                              market_trend: TrendType,
                              long_term_trend: TrendType,
                              df: pd.DataFrame) -> Dict:
        """최종 신호를 평가하고 결과를 반환합니다."""
        
        # 시장 추세에 따른 임계값 조정
        adjusted_threshold = self._get_adjusted_threshold(market_trend)
        
        strong_buy_signal = buy_score >= adjusted_threshold and buy_score > sell_score
        strong_sell_signal = sell_score >= adjusted_threshold and sell_score > buy_score
        
        latest_data = df.iloc[-1]
        
        if strong_buy_signal and long_term_trend == TrendType.BULLISH:
            logger.info(f"BUY SIGNAL CONFIRMED for {ticker} (Score: {buy_score:.2f})")
            
            stop_loss_price = self._calculate_stop_loss(df, 'buy')
            
            return {
                'type': 'BUY',
                'score': int(buy_score),
                'details': buy_details,
                'current_price': latest_data['Close'],
                'timestamp': latest_data.name.to_pydatetime(),
                'stop_loss_price': stop_loss_price
            }
            
        elif strong_sell_signal and long_term_trend == TrendType.BEARISH:
            logger.info(f"SELL SIGNAL CONFIRMED for {ticker} (Score: {sell_score:.2f})")
            
            stop_loss_price = self._calculate_stop_loss(df, 'sell')
            
            return {
                'type': 'SELL',
                'score': int(sell_score),
                'details': sell_details,
                'current_price': latest_data['Close'],
                'timestamp': latest_data.name.to_pydatetime(),
                'stop_loss_price': stop_loss_price
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