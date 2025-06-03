# indicator_calculator.py

import pandas as pd
import logging
import pandas_ta # pandas_ta를 pandas DataFrame에 등록하기 위해 추가

logger = logging.getLogger(__name__)

# --- 일봉 데이터용 지표 계산 함수 ---
def calculate_daily_indicators(df_daily: pd.DataFrame, fib_lookback_days: int) -> tuple[pd.DataFrame, dict]:
    """
    일봉 데이터에 기반한 예측용 지표들을 계산합니다.
    (피봇 포인트, 피보나치, ATR)
    """
    if df_daily.empty:
        logger.warning("Daily DataFrame is empty, cannot calculate daily indicators.")
        return df_daily, {}

    # 1. ATR (Average True Range)
    # ATR은 변동성 측정에 사용되며, 가격 범위 설정에 유용합니다.
    # df_daily.ta.atr()은 ATR 컬럼을 반환하지만, append=True로 DataFrame에 바로 추가.
    df_daily.ta.atr(append=True)

    # 2. Pivot Points (피봇 포인트)
    # 전일의 고가, 저가, 종가를 기준으로 다음 날의 지지/저항 수준을 예측
    # df_daily의 마지막 행은 전일 데이터 (가장 최신)
    if len(df_daily) < 1:
        logger.warning("Not enough data for Pivot Points calculation (need at least one day).")
        return df_daily, {}

    last_day_ohlc = df_daily.iloc[-1]
    prev_high = last_day_ohlc['High']
    prev_low = last_day_ohlc['Low']
    prev_close = last_day_ohlc['Close']

    pivot_point = (prev_high + prev_low + prev_close) / 3
    r1 = (2 * pivot_point) - prev_low
    s1 = (2 * pivot_point) - prev_high
    s2 = pivot_point - (prev_high - prev_low)
    r2 = pivot_point + (prev_high - prev_low)


    logger.debug(f"Calculated Pivot Points: P={pivot_point:.2f}, S1={s1:.2f}, R1={r1:.2f}, S2={s2:.2f}, R2={r2:.2f}")

    # 3. Fibonacci Retracement (피보나치 되돌림)
    # 최근 특정 기간의 스윙(고점-저점)을 기준으로 잠재적 지지/저항 수준 계산
    fib_data = df_daily.tail(fib_lookback_days)
    if fib_data.empty or len(fib_data) < 2:
        logger.warning(f"Not enough data for Fibonacci retracement (lookback {fib_lookback_days} days).")
        fib_levels = {} # 데이터 부족 시 빈 딕셔너리
    else:
        recent_high = fib_data['High'].max()
        recent_low = fib_data['Low'].min()
        price_range = recent_high - recent_low

        fib_levels = {
            '23.6%': recent_high - (price_range * 0.236),
            '38.2%': recent_high - (price_range * 0.382),
            '50.0%': recent_high - (price_range * 0.500),
            '61.8%': recent_high - (price_range * 0.618),
            '78.6%': recent_high - (price_range * 0.786),
        }
        logger.debug(f"Calculated Fibonacci Retracement Levels (from {recent_low:.2f} to {recent_high:.2f}): {fib_levels}")

    # ATR 컬럼은 DataFrame에 추가되므로 반환 시 포함됩니다.
    # 피봇 포인트와 피보나치 레벨은 DataFrame에 추가하기보다는 개별 값으로 반환하여 예측 모듈에서 사용
    return df_daily, {
        'pivot_points': {'P': pivot_point, 'S1': s1, 'S2': s2, 'R1': r1, 'R2': r2},
        'fib_retracement': fib_levels
    }


# --- 1분봉 데이터용 지표 계산 함수 ---
def calculate_intraday_indicators(df_intraday: pd.DataFrame) -> pd.DataFrame:
    """
    1분봉 데이터에 기반한 실시간 신호 감지용 지표들을 계산합니다.
    """
    if df_intraday.empty:
        logger.warning("Intraday DataFrame is empty, cannot calculate intraday indicators.")
        return df_intraday

    # 1. 이동평균선 (SMA)
    df_intraday.ta.sma(length=5, append=True)
    df_intraday.ta.sma(length=20, append=True)
    df_intraday.ta.sma(length=60, append=True)

    # 2. 상대강도지수 (RSI)
    df_intraday.ta.rsi(length=14, append=True)

    # 3. MACD (Moving Average Convergence Divergence)
    # 기본 설정: fast=12, slow=26, signal=9
    df_intraday.ta.macd(append=True)

    # 4. 스토캐스틱 오실레이터 (Stochastic Oscillator)
    # 기본 설정: k=14, d=3, smooth_k=3
    df_intraday.ta.stoch(append=True)

    # 5. ADX (Average Directional Index)
    # 기본 설정: length=14
    df_intraday.ta.adx(append=True) # ADX_14, DMN_14, DMP_14 컬럼 생성

    # 6. 볼린저 밴드 (Bollinger Bands)
    # 기본 설정: length=20, std=2.0
    df_intraday.ta.bbands(length=20, append=True) # length 명시적으로 20으로 설정

    # 7. 켈트너 채널 (Keltner Channels)
    # 기본 설정: length=20, scalar=2 (pandas_ta는 kc_length, kc_scalar 사용)
    # mamode='ema'를 명시하여 KCLe, KCMe, KCUe 컬럼이 생성되도록 함
    df_intraday.ta.kc(length=20, append=True, mamode='ema')

    # 8. 거래량 이동평균 (거래량 필터링을 위함)
    df_intraday['Volume_SMA_20'] = df_intraday['Volume'].rolling(window=20).mean()

    # 지표 계산 후 NaN 값 제거 (초반 계산 기간에 NaN이 발생)
    # 주의: 너무 많은 NaN을 제거하면 데이터가 부족해질 수 있으니, 최소한의 데이터는 남도록 확인
    df_intraday.dropna(inplace=True)

    # --- 추가할 진단 코드 ---
    logger.info(f"DEBUG: Columns after indicator calculation: {df_intraday.columns.tolist()}")
    logger.info(f"DEBUG: Keltner Channels columns: {[col for col in df_intraday.columns if 'KC' in col]}")
# --- 진단 코드 끝 ---

    return df_intraday
