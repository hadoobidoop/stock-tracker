from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from ...base.signal_detector import SignalDetector

logger = get_logger(__name__)


class CompositeSignalDetector(SignalDetector):
    """여러 감지기를 조합한 복합 신호 감지기"""
    
    def __init__(self, detectors: List[SignalDetector], weight: float, require_all: bool = False, name: str = None):
        super().__init__(weight, name or "Composite_Detector")
        self.detectors = detectors
        self.require_all = require_all  # True: 모든 감지기가 신호를 감지해야 함, False: 하나라도 감지하면 됨
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """복합 신호를 감지합니다."""
        
        if not self.detectors:
            return 0.0, 0.0, [], []
        
        all_buy_signals = []
        all_sell_signals = []
        all_buy_details = []
        all_sell_details = []
        
        # 각 감지기로부터 신호 수집
        for detector in self.detectors:
            try:
                buy_score, sell_score, buy_details, sell_details = detector.detect_signals(
                    df, market_trend, long_term_trend, daily_extra_indicators
                )
                
                if buy_score > 0:
                    all_buy_signals.append(buy_score)
                    all_buy_details.extend(buy_details)
                
                if sell_score > 0:
                    all_sell_signals.append(sell_score)
                    all_sell_details.extend(sell_details)
                    
            except Exception as e:
                logger.error(f"Error in composite detector {detector.name}: {e}")
                continue
        
        # 복합 신호 판단
        final_buy_score = 0.0
        final_sell_score = 0.0
        
        if self.require_all:
            # 모든 감지기가 신호를 감지해야 함
            if len(all_buy_signals) == len(self.detectors):
                final_buy_score = self.weight
            if len(all_sell_signals) == len(self.detectors):
                final_sell_score = self.weight
        else:
            # 하나라도 감지하면 됨
            if all_buy_signals:
                final_buy_score = self.weight
            if all_sell_signals:
                final_sell_score = self.weight
        
        return final_buy_score, final_sell_score, all_buy_details, all_sell_details


class MultiTimeframeCompositeDetector(SignalDetector):
    """다중 시간대 분석을 위한 복합 신호 감지기"""
    
    def __init__(self, weight: float, name: str = None):
        super().__init__(weight, name or "MultiTimeframe_Composite_Detector")
        self.required_daily_columns = ['SMA_20', 'SMA_50', 'RSI_14', 'ADX_14']
        self.required_hourly_columns = ['SMA_5', 'SMA_20', 'MACD_12_26_9', 'MACDs_12_26_9', 'RSI_14', 'ATR_14']
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """다중 시간대 복합 신호를 감지합니다."""
        
        # daily_extra_indicators에서 일봉 데이터 추출
        daily_df = daily_extra_indicators.get('daily_data') if daily_extra_indicators else None
        
        if daily_df is None or daily_df.empty:
            logger.warning("No daily data available for multi-timeframe analysis")
            return 0.0, 0.0, [], []
        
        # 시간봉 데이터는 df 파라미터에서 가져옴
        hourly_df = df
        
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        
        try:
            # 1. 데이터 유효성 검증
            if not self._validate_multi_timeframe_data(daily_df, hourly_df):
                return 0.0, 0.0, [], []
            
            # 2. 다중 시간대 추세 분석
            trend_analysis = self._analyze_multi_timeframe_trends(daily_df, hourly_df)
            
            # 3. 신호 강도 계산
            signal_strength = self._calculate_signal_strength(daily_df, hourly_df, trend_analysis)
            
            # 4. 최종 신호 결정
            if signal_strength['buy_strength'] > 0.5:  # 50% 이상의 신뢰도로 완화
                buy_score = self.weight * signal_strength['buy_strength']
                buy_details.append(f"다중시간대 매수 신호 (일봉:{trend_analysis['daily_trend']}, "
                                 f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['buy_strength']:.2f})")
            
            if signal_strength['sell_strength'] > 0.5:  # 50% 이상의 신뢰도로 완화
                sell_score = self.weight * signal_strength['sell_strength']
                sell_details.append(f"다중시간대 매도 신호 (일봉:{trend_analysis['daily_trend']}, "
                                  f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['sell_strength']:.2f})")
        
        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
        
        return buy_score, sell_score, buy_details, sell_details
    
    def _validate_multi_timeframe_data(self, daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> bool:
        """다중 시간대 데이터 유효성 검증"""
        try:
            # 일봉 데이터 검증 (최소 50일)
            if daily_df.empty or len(daily_df) < 50:
                return False
            
            # 시간봉 데이터 검증 (최소 48시간)
            if hourly_df.empty or len(hourly_df) < 48:
                return False
            
            # 필수 컬럼 존재 여부 확인
            daily_missing = [col for col in self.required_daily_columns if col not in daily_df.columns]
            hourly_missing = [col for col in self.required_hourly_columns if col not in hourly_df.columns]
            
            if daily_missing or hourly_missing:
                logger.warning(f"Missing columns - Daily: {daily_missing}, Hourly: {hourly_missing}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating multi-timeframe data: {e}")
            return False
    
    def _analyze_multi_timeframe_trends(self, daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> Dict[str, str]:
        """다중 시간대 추세 분석"""
        try:
            analysis = {
                'daily_trend': 'NEUTRAL',
                'hourly_trend': 'NEUTRAL',
                'consensus': 'NEUTRAL',
                'daily_strength': 0.0,
                'hourly_strength': 0.0
            }
            
            # 일봉 추세 분석 (SMA_20, SMA_50 활용)
            daily_latest = daily_df.iloc[-1]
            if 'SMA_20' in daily_df.columns and 'SMA_50' in daily_df.columns:
                sma20 = daily_latest['SMA_20']
                sma50 = daily_latest['SMA_50']
                close = daily_latest['Close']
                
                if not pd.isna(sma20) and not pd.isna(sma50):
                    if close > sma20 > sma50:
                        analysis['daily_trend'] = 'BULLISH'
                        analysis['daily_strength'] = min((close - sma50) / sma50 * 10, 1.0)
                    elif close < sma20 < sma50:
                        analysis['daily_trend'] = 'BEARISH'
                        analysis['daily_strength'] = min((sma50 - close) / sma50 * 10, 1.0)
            
            # 시간봉 추세 분석 (SMA_5, SMA_20 활용)
            hourly_latest = hourly_df.iloc[-1]
            if 'SMA_5' in hourly_df.columns and 'SMA_20' in hourly_df.columns:
                sma5 = hourly_latest['SMA_5']
                sma20 = hourly_latest['SMA_20']
                close = hourly_latest['Close']
                
                if not pd.isna(sma5) and not pd.isna(sma20):
                    if close > sma5 > sma20:
                        analysis['hourly_trend'] = 'BULLISH'
                        analysis['hourly_strength'] = min((close - sma20) / sma20 * 10, 1.0)
                    elif close < sma5 < sma20:
                        analysis['hourly_trend'] = 'BEARISH'
                        analysis['hourly_strength'] = min((sma20 - close) / sma20 * 10, 1.0)
            
            # 컨센서스 계산
            if analysis['daily_trend'] == analysis['hourly_trend'] and analysis['daily_trend'] != 'NEUTRAL':
                analysis['consensus'] = analysis['daily_trend']
            elif analysis['daily_trend'] != 'NEUTRAL' or analysis['hourly_trend'] != 'NEUTRAL':
                analysis['consensus'] = 'MIXED'
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing multi-timeframe trends: {e}")
            return {'daily_trend': 'NEUTRAL', 'hourly_trend': 'NEUTRAL', 'consensus': 'NEUTRAL', 
                   'daily_strength': 0.0, 'hourly_strength': 0.0}
    
    def _calculate_signal_strength(self, daily_df: pd.DataFrame, hourly_df: pd.DataFrame, 
                                  trend_analysis: Dict[str, str]) -> Dict[str, float]:
        """신호 강도 계산"""
        try:
            strength = {
                'buy_strength': 0.0,
                'sell_strength': 0.0
            }
            
            # 추세 일치도에 따른 기본 점수 (상향 조정)
            consensus_multiplier = {
                'BULLISH': 1.2,   # 20% 상향
                'BEARISH': 1.2,   # 20% 상향
                'MIXED': 0.8,     # 30% 상향
                'NEUTRAL': 0.5    # 30% 상향
            }
            
            base_multiplier = consensus_multiplier.get(trend_analysis['consensus'], 0.5)
            
            # 일봉 RSI 확인 (과매수/과매도 필터)
            daily_rsi = daily_df.iloc[-1].get('RSI_14', 50)
            hourly_rsi = hourly_df.iloc[-1].get('RSI_14', 50)
            
            # 매수 신호 강도 (RSI 기준 완화)
            if trend_analysis['consensus'] in ['BULLISH', 'MIXED']:  # MIXED도 허용
                rsi_factor = 1.0
                if daily_rsi < 75 and hourly_rsi < 85:  # 과매수 기준 완화
                    rsi_factor = 1.2
                elif daily_rsi > 85:  # 과매수 기준 완화
                    rsi_factor = 0.5  # 페널티 완화
                
                strength['buy_strength'] = (base_multiplier * rsi_factor * 
                                          max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                                          max(trend_analysis.get('hourly_strength', 0.5), 0.5))
            
            # 매도 신호 강도 (RSI 기준 완화)
            if trend_analysis['consensus'] in ['BEARISH', 'MIXED']:  # MIXED도 허용
                rsi_factor = 1.0
                if daily_rsi > 25 and hourly_rsi > 15:  # 과매도 기준 완화
                    rsi_factor = 1.2
                elif daily_rsi < 15:  # 과매도 기준 완화
                    rsi_factor = 0.5  # 페널티 완화
                
                strength['sell_strength'] = (base_multiplier * rsi_factor * 
                                           max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                                           max(trend_analysis.get('hourly_strength', 0.5), 0.5))
            
            return strength
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return {'buy_strength': 0.0, 'sell_strength': 0.0}