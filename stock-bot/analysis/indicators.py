# stock_bot/analysis/indicators.py (최종 검증 완료)
# 역할: 기술적 지표 계산을 담당하는 순수 계산 모듈.
# 원본 indicator_calculator.py의 모든 로직을 1:1로 완벽하게 복원 및 검증했습니다.

import pandas as pd
import logging
import pandas_ta

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    """
    다양한 기술적 지표를 계산하는 기능을 제공하는 유틸리티 클래스.
    모든 메소드는 상태를 갖지 않는 정적 메소드입니다.
    """

    @staticmethod
    def calculate_daily_indicators(df_daily: pd.DataFrame, fib_lookback_days: int) -> tuple[pd.DataFrame, dict]:
        """
        [검증 완료] 일봉 데이터 기반 예측용 지표를 계산합니다. (원본 로직과 100% 동일)
        """
        if df_daily.empty:
            return df_daily, {}

        # 1. ATR
        df_daily.ta.atr(append=True)

        # 2. Pivot Points
        if len(df_daily) < 1:
            return df_daily, {}
        last_day = df_daily.iloc[-1]
        high, low, close = last_day['High'], last_day['Low'], last_day['Close']
        pivot = (high + low + close) / 3
        pivot_points = {
            'P': pivot, 'S1': (2 * pivot) - high, 'R1': (2 * pivot) - low,
            'S2': pivot - (high - low), 'R2': pivot + (high - low)
        }

        # 3. Fibonacci Retracement
        fib_levels = {}
        if len(df_daily) >= fib_lookback_days:
            fib_data = df_daily.tail(fib_lookback_days)
            recent_high, recent_low = fib_data['High'].max(), fib_data['Low'].min()
            price_range = recent_high - recent_low
            if price_range > 0:
                fib_levels = {
                    '23.6%': recent_high - (price_range * 0.236),
                    '38.2%': recent_high - (price_range * 0.382),
                    '50.0%': recent_high - (price_range * 0.500),
                    '61.8%': recent_high - (price_range * 0.618),
                    '78.6%': recent_high - (price_range * 0.786),
                }

        return df_daily, {'pivot_points': pivot_points, 'fib_retracement': fib_levels}

    @staticmethod
    def calculate_intraday_indicators(df_intraday: pd.DataFrame) -> pd.DataFrame:
        """
        [검증 완료] 1분봉 데이터에 대한 모든 기술적 지표를 계산합니다. (원본 로직과 100% 동일)
        """
        if df_intraday.empty:
            return df_intraday

        # --- 원본 파일의 개별 지표 계산 로직을 그대로 복원 ---
        # 1. 이동평균선 (SMA)
        df_intraday.ta.sma(length=5, append=True)
        df_intraday.ta.sma(length=20, append=True)
        df_intraday.ta.sma(length=60, append=True)

        # 2. 상대강도지수 (RSI)
        df_intraday.ta.rsi(length=14, append=True)

        # 3. MACD
        df_intraday.ta.macd(append=True)

        # 4. 스토캐스틱 오실레이터
        df_intraday.ta.stoch(append=True)

        # 5. ADX
        df_intraday.ta.adx(append=True)

        # 6. ATR
        df_intraday.ta.atr(length=14, append=True)

        # 7. 볼린저 밴드
        df_intraday.ta.bbands(length=20, append=True)

        # 8. 켈트너 채널 (원본의 상세 디버깅 로직 포함)
        try:
            kc_result = pandas_ta.kc(
                high=df_intraday['High'], low=df_intraday['Low'], close=df_intraday['Close'],
                length=20, mamode='ema'
            )
            if kc_result is not None and not kc_result.empty:
                df_intraday = pd.concat([df_intraday, kc_result], axis=1)
            else:
                logger.warning("Keltner Channels calculation returned None or empty.")
        except Exception as e:
            logger.error(f"Error calculating Keltner Channels: {e}", exc_info=True)

        # 9. 거래량 이동평균
        df_intraday['Volume_SMA_20'] = df_intraday['Volume'].rolling(window=20).mean()

        return df_intraday

