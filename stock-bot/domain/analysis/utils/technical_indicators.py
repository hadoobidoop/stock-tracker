"""
기술적 지표 계산을 위한 유틸리티 모듈
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from infrastructure.logging import get_logger

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
    df[f'BBM_{period}_{std_dev}_0'] = df['Close'].rolling(window=period).mean()
    bb_std = df['Close'].rolling(window=period).std()
    df[f'BBU_{period}_{std_dev}_0'] = df[f'BBM_{period}_{std_dev}_0'] + (bb_std * std_dev)
    df[f'BBL_{period}_{std_dev}_0'] = df[f'BBM_{period}_{std_dev}_0'] - (bb_std * std_dev)
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
    
    # +DM, -DM 계산
    high_diff = df['High'].diff()
    low_diff = df['Low'].diff()
    
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
    
    # True Range 계산
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift())
    tr3 = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed values
    tr_smooth = tr.rolling(window=period).mean()
    plus_dm_smooth = pd.Series(plus_dm).rolling(window=period).mean()
    minus_dm_smooth = pd.Series(minus_dm).rolling(window=period).mean()
    
    # +DI, -DI 계산
    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)
    
    # DX 계산
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # ADX 계산
    df[f'ADX_{period}'] = dx.rolling(window=period).mean()
    df[f'DMP_{period}'] = plus_di
    df[f'DMN_{period}'] = minus_di
    
    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술적 지표를 계산합니다."""
    try:
        from domain.analysis.config.analysis_settings import TECHNICAL_INDICATORS
        
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
        
        return df
    except Exception as e:
        logger.error(f"Error calculating all indicators: {e}")
        return df


def calculate_fibonacci_levels(df: pd.DataFrame) -> Dict[str, float]:
    """피보나치 레벨을 계산합니다."""
    try:
        from domain.analysis.config.analysis_settings import FIBONACCI_LEVELS
        
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