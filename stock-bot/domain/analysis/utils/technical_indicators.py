"""
기술적 지표 계산을 위한 유틸리티 모듈
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from infrastructure.logging import get_logger
from domain.analysis.config.technical_indicator_settings import TECHNICAL_INDICATORS
from domain.analysis.config.technical_indicator_settings import FIBONACCI_LEVELS
from domain.analysis.config.technical_indicator_settings import HOURLY_INDICATORS
from domain.analysis.config.signals.realtime_signal_settings import REALTIME_SIGNAL_DETECTION

logger = get_logger(__name__)


def calculate_sma(df: pd.DataFrame, periods: list) -> pd.DataFrame:
    """이동평균선을 계산합니다."""
    df = df.copy()
    for period in periods:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI(Relative Strength Index)를 계산합니다."""
    df = df.copy()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD를 계산합니다."""
    df = df.copy()
    exp1 = df['Close'].ewm(span=fast).mean()
    exp2 = df['Close'].ewm(span=slow).mean()
    df[f'MACD_{fast}_{slow}_{signal}'] = exp1 - exp2
    df[f'MACDs_{fast}_{slow}_{signal}'] = df[f'MACD_{fast}_{slow}_{signal}'].ewm(span=signal).mean()
    df[f'MACDh_{fast}_{slow}_{signal}'] = df[f'MACD_{fast}_{slow}_{signal}'] - df[f'MACDs_{fast}_{slow}_{signal}']
    return df


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """스토캐스틱을 계산합니다."""
    df = df.copy()
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    df[f'STOCHk_{k_period}_{d_period}_{d_period}'] = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    df[f'STOCHd_{k_period}_{d_period}_{d_period}'] = df[f'STOCHk_{k_period}_{d_period}_{d_period}'].rolling(window=d_period).mean()
    return df


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """볼린저 밴드를 계산합니다."""
    df = df.copy()
    # std_dev를 정수로 변환하여 일관된 컬럼명 사용
    std_dev_int = int(std_dev)
    df[f'BBM_{period}_{std_dev_int}_0'] = df['Close'].rolling(window=period).mean()
    bb_std = df['Close'].rolling(window=period).std()
    df[f'BBU_{period}_{std_dev_int}_0'] = df[f'BBM_{period}_{std_dev_int}_0'] + (bb_std * std_dev)
    df[f'BBL_{period}_{std_dev_int}_0'] = df[f'BBM_{period}_{std_dev_int}_0'] - (bb_std * std_dev)
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """ATR(Average True Range)를 계산합니다."""
    df = df.copy()
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df[f'ATR_{period}'] = true_range.rolling(window=period).mean()
    return df


def calculate_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """거래량 이동평균을 계산합니다."""
    df = df.copy()
    df[f'Volume_SMA_{period}'] = df['Volume'].rolling(window=period).mean()
    return df


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """ADX(Average Directional Index)를 계산합니다."""
    df = df.copy()
    
    # 데이터가 충분하지 않으면 빈 컬럼들을 만들어서 반환
    if len(df) < period * 2:
        df[f'ADX_{period}'] = np.nan
        df[f'DMP_{period}'] = np.nan
        df[f'DMN_{period}'] = np.nan
        return df
    
    # +DM, -DM 계산
    high_diff = df['High'].diff()
    low_diff = df['Low'].diff()
    
    plus_dm = pd.Series(np.where((high_diff > -low_diff) & (high_diff > 0), high_diff, 0), index=df.index)
    minus_dm = pd.Series(np.where((-low_diff > high_diff) & (-low_diff > 0), -low_diff, 0), index=df.index)
    
    # True Range 계산
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift())
    tr3 = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder's smoothing (초기값 설정 후 점진적 업데이트)
    tr_smooth = tr.rolling(window=period).mean()
    plus_dm_smooth = plus_dm.rolling(window=period).mean()
    minus_dm_smooth = minus_dm.rolling(window=period).mean()
    
    # +DI, -DI 계산 (0으로 나누기 방지)
    # tr_smooth가 0이거나 NaN인 경우를 처리
    tr_smooth_safe = tr_smooth.replace(0, np.nan).ffill()
    
    plus_di = 100 * (plus_dm_smooth / tr_smooth_safe)
    minus_di = 100 * (minus_dm_smooth / tr_smooth_safe)
    
    # DX 계산
    sum_di = plus_di + minus_di
    # sum_di가 0이거나 매우 작은 값일 때를 처리
    dx = pd.Series(index=df.index, dtype=float)
    valid_mask = (sum_di > 0.001) & sum_di.notna()
    dx.loc[valid_mask] = 100 * abs(plus_di - minus_di).loc[valid_mask] / sum_di.loc[valid_mask]
    
    # ADX 계산 (단순 이동평균)
    adx = dx.rolling(window=period).mean()
    
    df[f'ADX_{period}'] = adx
    df[f'DMP_{period}'] = plus_di
    df[f'DMN_{period}'] = minus_di
    
    return df


def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, atr_multiplier: float = 2.0) -> pd.DataFrame:
    """켈트너 채널을 계산합니다."""
    df = df.copy()
    
    # EMA 계산 (중심선)
    df[f'kcbe_{period}_{int(atr_multiplier)}'] = df['Close'].ewm(span=period).mean()
    
    # ATR 계산
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    # 상단선과 하단선 계산
    df[f'kcue_{period}_{int(atr_multiplier)}'] = df[f'kcbe_{period}_{int(atr_multiplier)}'] + (atr * atr_multiplier)
    df[f'kcle_{period}_{int(atr_multiplier)}'] = df[f'kcbe_{period}_{int(atr_multiplier)}'] - (atr * atr_multiplier)
    
    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술적 지표를 계산합니다."""
    try:
        df = df.copy()
        
        # 설정값 가져오기
        sma_periods = TECHNICAL_INDICATORS["SMA_PERIODS"]
        rsi_period = TECHNICAL_INDICATORS["RSI_PERIOD"]
        macd_fast = TECHNICAL_INDICATORS["MACD_FAST"]
        macd_slow = TECHNICAL_INDICATORS["MACD_SLOW"]
        macd_signal = TECHNICAL_INDICATORS["MACD_SIGNAL"]
        stoch_k_period = TECHNICAL_INDICATORS["STOCH_K_PERIOD"]
        stoch_d_period = TECHNICAL_INDICATORS["STOCH_D_PERIOD"]
        bb_period = TECHNICAL_INDICATORS["BB_PERIOD"]
        bb_std_dev = TECHNICAL_INDICATORS["BB_STD_DEV"]
        atr_period = TECHNICAL_INDICATORS["ATR_PERIOD"]
        volume_sma_period = TECHNICAL_INDICATORS["VOLUME_SMA_PERIOD"]
        adx_period = TECHNICAL_INDICATORS["ADX_PERIOD"]
        
        # 기본 지표들 계산
        df = calculate_sma(df, sma_periods)
        df = calculate_rsi(df, rsi_period)
        df = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df = calculate_stochastic(df, stoch_k_period, stoch_d_period)
        df = calculate_bollinger_bands(df, bb_period, bb_std_dev)
        df = calculate_atr(df, atr_period)
        df = calculate_volume_sma(df, volume_sma_period)
        df = calculate_adx(df, adx_period)
        
        # 켈트너 채널 계산 추가
        df = calculate_keltner_channels(df, bb_period, bb_std_dev)  # 볼린저 밴드와 동일한 파라미터 사용
        
        return df
    except Exception as e:
        logger.error(f"Error calculating all indicators: {e}")
        return df


def calculate_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """피보나치 레벨을 계산합니다."""
    try:
        # 설정값 가져오기
        levels = FIBONACCI_LEVELS["LEVELS"]
        lookback_days = FIBONACCI_LEVELS["LOOKBACK_DAYS"]
        
        # lookback_days만큼의 데이터 사용
        if len(df) > lookback_days:
            df_subset = df.tail(lookback_days)
        else:
            df_subset = df
        
        high = df_subset['High'].max()
        low = df_subset['Low'].min()
        diff = high - low
        
        fib_levels = {}
        for level in levels:
            if level == 0:
                fib_levels['fib_0'] = low
            elif level == 100:
                fib_levels['fib_100'] = high
            else:
                fib_levels[f'fib_{level}'] = low + (diff * level / 100)
        
        return fib_levels
    except Exception as e:
        logger.error(f"Error calculating Fibonacci levels: {e}")
        return {}


def get_trend_direction(df: pd.DataFrame, short_period: int = 20, long_period: int = 50) -> str:
    """추세 방향을 판단합니다."""
    try:
        if len(df) < long_period:
            return "NEUTRAL"
        
        short_sma = df['Close'].rolling(window=short_period).mean().iloc[-1]
        long_sma = df['Close'].rolling(window=long_period).mean().iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        if pd.isna(short_sma) or pd.isna(long_sma):
            return "NEUTRAL"
        
        if current_price > short_sma > long_sma:
            return "BULLISH"
        elif current_price < short_sma < long_sma:
            return "BEARISH"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"Error determining trend direction: {e}")
        return "NEUTRAL"


def calculate_daily_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """일봉 기반 장기 추세 지표를 계산합니다."""
    try:
        # 모든 기술적 지표를 계산 (시간봉과 동일하게)
        df = calculate_all_indicators(df)
        return df
    except Exception as e:
        logger.error(f"Error calculating daily indicators: {e}")
        return df


def calculate_hourly_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """시간봉 기반 단기 신호 지표를 계산합니다."""
    try:
        df = df.copy()
        
        # 설정값 가져오기
        sma_periods = HOURLY_INDICATORS["SMA_PERIODS"]
        rsi_period = HOURLY_INDICATORS["RSI_PERIOD"]
        macd_fast = HOURLY_INDICATORS["MACD_FAST"]
        macd_slow = HOURLY_INDICATORS["MACD_SLOW"]
        macd_signal = HOURLY_INDICATORS["MACD_SIGNAL"]
        stoch_k_period = HOURLY_INDICATORS["STOCH_K_PERIOD"]
        stoch_d_period = HOURLY_INDICATORS["STOCH_D_PERIOD"]
        atr_period = HOURLY_INDICATORS["ATR_PERIOD"]
        volume_sma_period = HOURLY_INDICATORS["VOLUME_SMA_PERIOD"]
        
        # 단기 신호 지표들 계산
        df = calculate_sma(df, sma_periods)
        df = calculate_rsi(df, rsi_period)
        df = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df = calculate_stochastic(df, stoch_k_period, stoch_d_period)
        df = calculate_atr(df, atr_period)
        df = calculate_volume_sma(df, volume_sma_period)
        
        return df
    except Exception as e:
        logger.error(f"Error calculating hourly indicators: {e}")
        return df


def calculate_multi_timeframe_indicators(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    다중 시간대 지표를 계산합니다.
    
    Args:
        daily_df: 일봉 데이터
        hourly_df: 시간봉 데이터
    
    Returns:
        Dict: {'daily': 일봉지표, 'hourly': 시간봉지표}
    """
    try:
        result = {}
        
        # 일봉 지표 계산
        if not daily_df.empty:
            result['daily'] = calculate_daily_indicators(daily_df)
            logger.debug(f"Calculated daily indicators: {len(result['daily'])} bars")
        
        # 시간봉 지표 계산
        if not hourly_df.empty:
            result['hourly'] = calculate_hourly_indicators(hourly_df)
            logger.debug(f"Calculated hourly indicators: {len(result['hourly'])} bars")
        
        return result
    except Exception as e:
        logger.error(f"Error calculating multi-timeframe indicators: {e}")
        return {'daily': pd.DataFrame(), 'hourly': pd.DataFrame()}


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
        
        # 일봉 추세 (SMA_50 기준, 1% 차이로 완화)
        if not daily_indicators.empty and 'SMA_50' in daily_indicators.columns:
            latest_close = daily_indicators.iloc[-1]['Close']
            latest_sma50 = daily_indicators.iloc[-1]['SMA_50']
            
            if not pd.isna(latest_sma50):
                if latest_close > latest_sma50 * 1.01:  # 1% 이상 위
                    result['daily_trend'] = 'BULLISH'
                elif latest_close < latest_sma50 * 0.99:  # 1% 이상 아래
                    result['daily_trend'] = 'BEARISH'
        
        # 시간봉 추세 (SMA_20 및 추가 지표 활용)
        if not hourly_indicators.empty and 'SMA_20' in hourly_indicators.columns:
            latest_close = hourly_indicators.iloc[-1]['Close']
            latest_sma20 = hourly_indicators.iloc[-1]['SMA_20']
            
            if not pd.isna(latest_sma20):
                # RSI를 추가 지표로 활용
                rsi_14 = hourly_indicators.iloc[-1].get('RSI_14', 50)
                
                if latest_close > latest_sma20:
                    if rsi_14 > 50:  # RSI가 50 이상이면 상승 추세 확인
                        result['hourly_trend'] = 'BULLISH'
                elif latest_close < latest_sma20:
                    if rsi_14 < 50:  # RSI가 50 미만이면 하락 추세 확인
                        result['hourly_trend'] = 'BEARISH'
        
        # 컨센서스 판단 (하나라도 강한 신호가 있으면 반영)
        if result['daily_trend'] == result['hourly_trend']:
            result['consensus'] = result['daily_trend']
        elif result['daily_trend'] != 'NEUTRAL':
            result['consensus'] = result['daily_trend']  # 일봉 우선
        elif result['hourly_trend'] != 'NEUTRAL':
            result['consensus'] = result['hourly_trend']  # 시간봉 차선
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
        
        # 설정에서 최소 요구사항 가져오기
        min_daily_length = REALTIME_SIGNAL_DETECTION["MIN_DAILY_DATA_LENGTH"]  # 120개
        min_hourly_length = REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]  # 30개 (수정됨)
        
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