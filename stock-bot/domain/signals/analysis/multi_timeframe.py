# Multi-Timeframe Analysis Functions
# =====================================
# 다중 시간대 분석 관련 함수들 - 일봉/시간봉 동시 분석, 추세 컨센서스, 신호 강도 계산

from typing import Dict, Tuple, List

import pandas as pd

from infrastructure.logging import get_logger

logger = get_logger(__name__)


def validate_multi_timeframe_data(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> bool:
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
            
        required_daily_columns = ['SMA_20', 'SMA_50', 'RSI_14', 'ADX_14']
        required_hourly_columns = ['SMA_5', 'SMA_20', 'MACD_12_26_9', 'MACDs_12_26_9', 'RSI_14', 'ATR_14']
        
        daily_missing = [col for col in required_daily_columns if col not in daily_df.columns]
        hourly_missing = [col for col in required_hourly_columns if col not in hourly_df.columns]
        
        if daily_missing or hourly_missing:
            logger.warning(f"Missing columns - Daily: {daily_missing}, Hourly: {hourly_missing}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating multi-timeframe data: {e}")
        return False


def analyze_multi_timeframe_trends(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> Dict[str, str]:
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
        
        # 일봉 추세 분석
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
        
        # 시간봉 추세 분석
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
        
        # 컨센서스 결정
        if analysis['daily_trend'] == analysis['hourly_trend'] and analysis['daily_trend'] != 'NEUTRAL':
            analysis['consensus'] = analysis['daily_trend']
        elif analysis['daily_trend'] != 'NEUTRAL' or analysis['hourly_trend'] != 'NEUTRAL':
            analysis['consensus'] = 'MIXED'
            
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing multi-timeframe trends: {e}")
        return {
            'daily_trend': 'NEUTRAL', 
            'hourly_trend': 'NEUTRAL', 
            'consensus': 'NEUTRAL',
            'daily_strength': 0.0, 
            'hourly_strength': 0.0
        }


def calculate_multi_timeframe_signal_strength(
    daily_df: pd.DataFrame, 
    hourly_df: pd.DataFrame,
    trend_analysis: Dict[str, str]
) -> Dict[str, float]:
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
        
        # RSI 기반 조정
        daily_rsi = daily_df.iloc[-1].get('RSI_14', 50)
        hourly_rsi = hourly_df.iloc[-1].get('RSI_14', 50)
        
        # 매수 강도 계산
        if trend_analysis['consensus'] in ['BULLISH', 'MIXED']:
            rsi_factor = 1.0
            if daily_rsi < 75 and hourly_rsi < 85:
                rsi_factor = 1.2
            elif daily_rsi > 85:
                rsi_factor = 0.5
                
            strength['buy_strength'] = (
                base_multiplier * rsi_factor * 
                max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                max(trend_analysis.get('hourly_strength', 0.5), 0.5)
            )
        
        # 매도 강도 계산
        if trend_analysis['consensus'] in ['BEARISH', 'MIXED']:
            rsi_factor = 1.0
            if daily_rsi > 25 and hourly_rsi > 15:
                rsi_factor = 1.2
            elif daily_rsi < 15:
                rsi_factor = 0.5
                
            strength['sell_strength'] = (
                base_multiplier * rsi_factor * 
                max(trend_analysis.get('daily_strength', 0.5), 0.5) * 
                max(trend_analysis.get('hourly_strength', 0.5), 0.5)
            )
        
        return strength
    except Exception as e:
        logger.error(f"Error calculating signal strength: {e}")
        return {'buy_strength': 0.0, 'sell_strength': 0.0}


def analyze_multi_timeframe_signals(
    daily_df: pd.DataFrame, 
    hourly_df: pd.DataFrame
) -> Tuple[Dict[str, float], List[str], List[str]]:
    """
    다중 시간대 종합 분석 - 전체 분석 과정을 통합한 메인 함수
    
    Args:
        daily_df (pd.DataFrame): 일봉 데이터
        hourly_df (pd.DataFrame): 시간봉 데이터
        
    Returns:
        Tuple[Dict[str, float], List[str], List[str]]: (신호강도, 매수근거, 매도근거)
    """
    buy_details = []
    sell_details = []
    
    # 데이터 유효성 검증
    if not validate_multi_timeframe_data(daily_df, hourly_df):
        return {'buy_strength': 0.0, 'sell_strength': 0.0}, buy_details, sell_details
    
    # 추세 분석
    trend_analysis = analyze_multi_timeframe_trends(daily_df, hourly_df)
    
    # 신호 강도 계산
    signal_strength = calculate_multi_timeframe_signal_strength(daily_df, hourly_df, trend_analysis)
    
    # 근거 생성
    if signal_strength['buy_strength'] > 0.5:
        buy_details.append(
            f"다중시간대 매수 신호 (일봉:{trend_analysis['daily_trend']}, "
            f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['buy_strength']:.2f})"
        )
    
    if signal_strength['sell_strength'] > 0.5:
        sell_details.append(
            f"다중시간대 매도 신호 (일봉:{trend_analysis['daily_trend']}, "
            f"시간봉:{trend_analysis['hourly_trend']}, 신뢰도:{signal_strength['sell_strength']:.2f})"
        )
    
    return signal_strength, buy_details, sell_details