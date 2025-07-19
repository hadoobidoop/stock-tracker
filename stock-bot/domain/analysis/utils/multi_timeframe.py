"""
다중 시간대(MultiTimeframe) 관련 유틸리티 함수 모음
- 신호 필터링, 데이터 유효성 검증, 추세 분석 등
- realtime_signal_detection_job, 전략 등에서 재사용 가능
"""
import logging
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


def _apply_multi_timeframe_filter(signal_result: Dict, multi_timeframe_analysis: Dict) -> Dict:
    """
    다중 시간대 분석 결과를 바탕으로 신호를 필터링합니다.
    Args:
        signal_result: 기존 신호 감지 결과
        multi_timeframe_analysis: 다중 시간대 분석 결과
    Returns:
        Dict: 필터링된 신호 결과 (조건에 맞지 않으면 빈 딕셔너리)
    """
    try:
        if not signal_result or not multi_timeframe_analysis:
            return signal_result

        signal_type = signal_result.get('type')
        consensus = multi_timeframe_analysis.get('consensus', 'NEUTRAL')
        daily_trend = multi_timeframe_analysis.get('daily_trend', 'NEUTRAL')
        hourly_trend = multi_timeframe_analysis.get('hourly_trend', 'NEUTRAL')

        # 매수 신호 필터링
        if signal_type == 'BUY':
            if consensus == 'BULLISH':
                signal_result['score'] = int(signal_result['score'] * 1.2)
                signal_result['details'].append("다중시간대 상승 확인으로 신호 강화")
                return signal_result
            elif hourly_trend == 'BULLISH' and daily_trend == 'NEUTRAL':
                signal_result['score'] = int(signal_result['score'] * 0.9)
                signal_result['details'].append("단기 상승 신호 (장기 추세 중립)")
                return signal_result
            elif daily_trend == 'BEARISH':
                logger.warning(f"Filtered out BUY signal due to bearish daily trend")
                return {}
        elif signal_type == 'SELL':
            if consensus == 'BEARISH':
                signal_result['score'] = int(signal_result['score'] * 1.2)
                signal_result['details'].append("다중시간대 하락 확인으로 신호 강화")
                return signal_result
            elif hourly_trend == 'BEARISH' and daily_trend == 'NEUTRAL':
                signal_result['score'] = int(signal_result['score'] * 0.9)
                signal_result['details'].append("단기 하락 신호 (장기 추세 중립)")
                return signal_result
            elif daily_trend == 'BULLISH':
                logger.warning(f"Filtered out SELL signal due to bullish daily trend")
                return {}
        return signal_result
    except Exception as e:
        logger.error(f"Error in multi-timeframe filter: {e}")
        return signal_result


def get_trend_direction_multi_timeframe(daily_indicators: pd.DataFrame, hourly_indicators: pd.DataFrame) -> Dict[str, str]:
    """
    다중 시간대 추세 방향을 분석합니다.
    Returns:
        Dict: {'daily_trend': '상승/하락/중립', 'hourly_trend': '상승/하락/중립', 'consensus': '일치/불일치'}
    """
    try:
        result = {
            'daily_trend': 'NEUTRAL',
            'hourly_trend': 'NEUTRAL',
            'consensus': 'NEUTRAL'
        }
        if not daily_indicators.empty and 'SMA_50' in daily_indicators.columns:
            latest_close = daily_indicators.iloc[-1]['Close']
            latest_sma50 = daily_indicators.iloc[-1]['SMA_50']
            if not pd.isna(latest_sma50):
                if latest_close > latest_sma50 * 1.01:
                    result['daily_trend'] = 'BULLISH'
                elif latest_close < latest_sma50 * 0.99:
                    result['daily_trend'] = 'BEARISH'
        if not hourly_indicators.empty and 'SMA_20' in hourly_indicators.columns:
            latest_close = hourly_indicators.iloc[-1]['Close']
            latest_sma20 = hourly_indicators.iloc[-1]['SMA_20']
            if not pd.isna(latest_sma20):
                rsi_14 = hourly_indicators.iloc[-1].get('RSI_14', 50)
                if latest_close > latest_sma20:
                    if rsi_14 > 50:
                        result['hourly_trend'] = 'BULLISH'
                elif latest_close < latest_sma20:
                    if rsi_14 < 50:
                        result['hourly_trend'] = 'BEARISH'
        if result['daily_trend'] == result['hourly_trend']:
            result['consensus'] = result['daily_trend']
        elif result['daily_trend'] != 'NEUTRAL':
            result['consensus'] = result['daily_trend']
        elif result['hourly_trend'] != 'NEUTRAL':
            result['consensus'] = result['hourly_trend']
        else:
            result['consensus'] = 'NEUTRAL'
        return result
    except Exception as e:
        logger.error(f"Error analyzing multi-timeframe trend: {e}")
        return {'daily_trend': 'NEUTRAL', 'hourly_trend': 'NEUTRAL', 'consensus': 'NEUTRAL'}


def validate_multi_timeframe_data(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> Dict[str, bool]:
    """
    다중 시간대 데이터의 유효성을 검증합니다.
    Returns:
        Dict: {'daily_valid': bool, 'hourly_valid': bool, 'sufficient_for_analysis': bool}
    """
    try:
        from domain.analysis.utils.technical_indicators import REALTIME_SIGNAL_DETECTION
        min_daily_length = REALTIME_SIGNAL_DETECTION["MIN_DAILY_DATA_LENGTH"]
        min_hourly_length = REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]
        daily_valid = not daily_df.empty and len(daily_df) >= min_daily_length
        hourly_valid = not hourly_df.empty and len(hourly_df) >= min_hourly_length
        return {
            'daily_valid': daily_valid,
            'hourly_valid': hourly_valid,
            'sufficient_for_analysis': daily_valid and hourly_valid,
            'daily_length': len(daily_df) if not daily_df.empty else 0,
            'hourly_length': len(hourly_df) if not hourly_df.empty else 0
        }
    except Exception as e:
        logger.error(f"Error validating multi-timeframe data: {e}")
        return {
            'daily_valid': False,
            'hourly_valid': False,
            'sufficient_for_analysis': False,
            'daily_length': 0,
            'hourly_length': 0
        } 