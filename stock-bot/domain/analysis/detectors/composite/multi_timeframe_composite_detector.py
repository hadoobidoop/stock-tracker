# MultiTimeframeCompositeDetector (다중 시간대 복합 Detector)
# =========================================================
# - 일봉/시간봉 데이터를 동시에 분석하여, 추세 컨센서스와 신호 강도를 산출하는 복합 신호 감지기
# - 단일 Detector로 일봉/시간봉 컨펌, 신뢰도 계산, 신호 강도(점수) 산출까지 일괄 처리
# - 신호 컨펌/강도 산출 로직을 커스터마이즈하거나, 추가 필터/지표를 결합해 확장 가능
# - MultiTimeframeStrategy에서 직접 사용하며, config에서 가중치/임계값 등 조정 가능
#
# [주요 기능]
#   - _validate_multi_timeframe_data: 입력 데이터(일봉/시간봉) 유효성 검증
#   - _analyze_multi_timeframe_trends: 일봉/시간봉 추세 및 컨센서스 분석
#   - _calculate_signal_strength: 컨센서스/지표 기반 신호 강도(점수) 산출
#   - detect_signals: 전체 분석 및 신호/점수/근거 반환 (전략에서 호출)
#
# [확장/유지보수 포인트]
#   - 신호 컨펌/강도 산출 로직(_analyze_multi_timeframe_trends, _calculate_signal_strength) 커스터마이즈 가능
#   - 신규 지표/필터 추가, 근거 메시지 포맷 확장 등 용이
#
# [사용 예시]
#   detector = MultiTimeframeCompositeDetector(weight=7.0)
#   buy_score, sell_score, buy_details, sell_details = detector.detect_signals(df, market_trend, long_term_trend, daily_extra_indicators)

from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from base.signal_detector import SignalDetector

logger = get_logger(__name__)

class MultiTimeframeCompositeDetector(SignalDetector):
    """
    다중 시간대 복합 신호 감지기
    - 일봉/시간봉 데이터를 동시에 분석하여, 추세 컨센서스와 신호 강도를 산출
    - 단일 Detector로 일봉/시간봉 컨펌, 신뢰도 계산, 신호 강도(점수) 산출까지 일괄 처리
    - 신호 컨펌/강도 산출 로직을 커스터마이즈하거나, 추가 필터/지표를 결합해 확장 가능
    """
    def __init__(self, weight: float, name: str = None):
        """
        MultiTimeframeCompositeDetector 생성자
        Args:
            weight (float): Detector 가중치(최종 점수에 곱해짐)
            name (str, optional): Detector 이름(미지정 시 기본값)
        """
        super().__init__(weight, name or "MultiTimeframe_Composite_Detector")
        self.required_daily_columns = ['SMA_20', 'SMA_50', 'RSI_14', 'ADX_14']
        self.required_hourly_columns = ['SMA_5', 'SMA_20', 'MACD_12_26_9', 'MACDs_12_26_9', 'RSI_14', 'ATR_14']

    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """
        일봉/시간봉 동시 분석 및 신호/점수/근거 반환
        Args:
            df (pd.DataFrame): 시간봉 데이터
            market_trend (TrendType): 시장 추세
            long_term_trend (TrendType): 장기 추세
            daily_extra_indicators (dict, optional): 일봉 데이터 등 추가 지표
        Returns:
            Tuple[float, float, List[str], List[str]]: (매수점수, 매도점수, 매수근거, 매도근거)
        """
        daily_df = daily_extra_indicators.get('daily_data') if daily_extra_indicators else None
        if daily_df is None or daily_df.empty:
            logger.warning("No daily data available for multi-timeframe analysis")
            return 0.0, 0.0, [], []
        hourly_df = df
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        try:
            if not self._validate_multi_timeframe_data(daily_df, hourly_df):
                return 0.0, 0.0, [], []
            trend_analysis = self._analyze_multi_timeframe_trends(daily_df, hourly_df)
            signal_strength = self._calculate_signal_strength(daily_df, hourly_df, trend_analysis)
            if signal_strength['buy_strength'] > 0.5:
                buy_score = self.weight * signal_strength['buy_strength']
                buy_details.append(f"다중시간대 매수 신호 (일봉:{trend_analysis['daily_trend']}, "
                                 f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['buy_strength']:.2f})")
            if signal_strength['sell_strength'] > 0.5:
                sell_score = self.weight * signal_strength['sell_strength']
                sell_details.append(f"다중시간대 매도 신호 (일봉:{trend_analysis['daily_trend']}, "
                                  f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['sell_strength']:.2f})")
        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
        return buy_score, sell_score, buy_details, sell_details

    def _validate_multi_timeframe_data(self, daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> bool:
        """
        입력 데이터(일봉/시간봉) 유효성 검증
        Args:
            daily_df (pd.DataFrame): 일봉 데이터
            hourly_df (pd.DataFrame): 시간봉 데이터
        Returns:
            bool: 유효성 통과 여부
        """
        try:
            if daily_df.empty or len(daily_df) < 50:
                return False
            if hourly_df.empty or len(hourly_df) < 48:
                return False
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
        """
        일봉/시간봉 추세 및 컨센서스 분석
        Args:
            daily_df (pd.DataFrame): 일봉 데이터
            hourly_df (pd.DataFrame): 시간봉 데이터
        Returns:
            Dict[str, str]: 추세/컨센서스/강도 등 분석 결과
        """
        try:
            analysis = {
                'daily_trend': 'NEUTRAL',
                'hourly_trend': 'NEUTRAL',
                'consensus': 'NEUTRAL',
                'daily_strength': 0.0,
                'hourly_strength': 0.0
            }
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
        """
        컨센서스/지표 기반 신호 강도(점수) 산출
        Args:
            daily_df (pd.DataFrame): 일봉 데이터
            hourly_df (pd.DataFrame): 시간봉 데이터
            trend_analysis (dict): 추세/컨센서스 분석 결과
        Returns:
            Dict[str, float]: {'buy_strength': float, 'sell_strength': float}
        """
        try:
            strength = {
                'buy_strength': 0.0,
                'sell_strength': 0.0
            }
            consensus_multiplier = {
                'BULLISH': 1.2,
                'BEARISH': 1.2,
                'MIXED': 0.8,
                'NEUTRAL': 0.5
            }
            base_multiplier = consensus_multiplier.get(trend_analysis['consensus'], 0.5)
            daily_rsi = daily_df.iloc[-1].get('RSI_14', 50)
            hourly_rsi = hourly_df.iloc[-1].get('RSI_14', 50)
            if trend_analysis['consensus'] in ['BULLISH', 'MIXED']:
                rsi_factor = 1.0
                if daily_rsi < 75 and hourly_rsi < 85:
                    rsi_factor = 1.2
                elif daily_rsi > 85:
                    rsi_factor = 0.5
                strength['buy_strength'] = (base_multiplier * rsi_factor * 
                                          max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                                          max(trend_analysis.get('hourly_strength', 0.5), 0.5))
            if trend_analysis['consensus'] in ['BEARISH', 'MIXED']:
                rsi_factor = 1.0
                if daily_rsi > 25 and hourly_rsi > 15:
                    rsi_factor = 1.2
                elif daily_rsi < 15:
                    rsi_factor = 0.5
                strength['sell_strength'] = (base_multiplier * rsi_factor * 
                                           max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                                           max(trend_analysis.get('hourly_strength', 0.5), 0.5))
            return strength
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return {'buy_strength': 0.0, 'sell_strength': 0.0} 