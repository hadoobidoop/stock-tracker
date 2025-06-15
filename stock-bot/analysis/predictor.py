import pandas as pd
import logging
from typing import Dict

from ..config import PREDICTION_ATR_MULTIPLIER_FOR_RANGE, PREDICTION_SIGNAL_WEIGHTS, PREDICTION_THRESHOLD
from ..database.models import TrendType
from .indicators import IndicatorCalculator

logger = logging.getLogger(__name__)

class PricePredictor:
    """
    과거 데이터를 기반으로 미래 가격 움직임(여기서는 다음 날 지지선)을 예측하는 클래스.
    """

    @staticmethod
    def predict_next_day_buy_price(df_daily: pd.DataFrame, ticker: str, long_term_trend: str) -> Dict:
        """
        전일 OHLCV 데이터를 기반으로 다음 날의 잠재적 매수 가격(지지선)을 예측합니다.
        (원본 price_predictor.py의 함수 로직과 100% 동일하게 복원)
        """
        if long_term_trend == TrendType.BEARISH:
            logger.debug(f"Prediction for {ticker} aborted as long-term trend is BEARISH.")
            return {}

        # 원본 파일의 FIB_LOOKBACK_DAYS를 60으로 가정하고, 충분한 데이터가 있는지 확인
        if df_daily.empty or len(df_daily) < 60:
            logger.warning(f"Not enough daily data to predict for {ticker}.")
            return {}

        # 일봉 지표 계산은 IndicatorCalculator에게 위임
        df_with_indicators, daily_extras = IndicatorCalculator.calculate_daily_indicators(df_daily, 60)

        if not daily_extras or not daily_extras.get('pivot_points'):
            logger.warning(f"Failed to get daily extra indicators for {ticker}.")
            return {}

        last_day = df_with_indicators.iloc[-1]
        atr_col = next((col for col in df_with_indicators.columns if col.startswith('ATR')), None)
        current_atr = last_day.get(atr_col, 0.0)

        proximity_threshold = (current_atr or 0) * PREDICTION_ATR_MULTIPLIER_FOR_RANGE

        pivot_points = daily_extras.get('pivot_points', {})
        fib_levels = daily_extras.get('fib_retracement', {})

        prediction_score = 0
        prediction_details = []
        potential_buy_info = {}

        # --- 예측 점수 계산 로직 (원본과 100% 동일하게 복원) ---

        # 1. 피봇 S2 근접 확인
        if 'S2' in pivot_points and abs(last_day['Close'] - pivot_points['S2']) <= proximity_threshold:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("pivot_s2_near", 0)
            prediction_details.append(f"Pivot S2 ({pivot_points['S2']:.2f}) 근접")
            if not potential_buy_info: potential_buy_info = {'price_type': 'Pivot S2', 'price': pivot_points['S2'], 'reason': "Close near Pivot S2"}

        # 2. 피보나치 61.8% 근접 확인
        if '61.8%' in fib_levels and abs(last_day['Close'] - fib_levels['61.8%']) <= proximity_threshold:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("fib_618_near", 0)
            prediction_details.append(f"Fib 61.8% ({fib_levels['61.8%']:.2f}) 근접")
            if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 61.8%', 'price': fib_levels['61.8%'], 'reason': "Close near Fib 61.8%"}

        # 3. 피봇 S1 근접 확인
        if 'S1' in pivot_points and abs(last_day['Close'] - pivot_points['S1']) <= proximity_threshold:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("pivot_s1_near", 0)
            prediction_details.append(f"Pivot S1 ({pivot_points['S1']:.2f}) 근접")
            if not potential_buy_info: potential_buy_info = {'price_type': 'Pivot S1', 'price': pivot_points['S1'], 'reason': "Close near Pivot S1"}

        # 4. 피보나치 50.0% 근접 확인
        if '50.0%' in fib_levels and abs(last_day['Close'] - fib_levels['50.0%']) <= proximity_threshold:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("fib_500_near", 0)
            prediction_details.append(f"Fib 50.0% ({fib_levels['50.0%']:.2f}) 근접")
            if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 50.0%', 'price': fib_levels['50.0%'], 'reason': "Close near Fib 50.0%"}

        # 5. 피보나치 38.2% 근접 확인
        if '38.2%' in fib_levels and abs(last_day['Close'] - fib_levels['38.2%']) <= proximity_threshold:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("fib_382_near", 0)
            prediction_details.append(f"Fib 38.2% ({fib_levels['38.2%']:.2f}) 근접")
            if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 38.2%', 'price': fib_levels['38.2%'], 'reason': "Close near Fib 38.2%"}

        # 6. 일일 RSI 과매도 확인
        rsi_col = next((col for col in df_with_indicators.columns if col.startswith('RSI')), None)
        if rsi_col and last_day.get(rsi_col, 100) <= 30:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("rsi_oversold_daily", 0)
            prediction_details.append(f"일일 RSI 과매도 ({last_day[rsi_col]:.2f})")

        # 7. 합리적 ATR 확인 (변동성 필터) - [검증 완료] 누락되었던 로직 복원
        if current_atr > 0 and (current_atr / last_day['Close']) < 0.05:
            prediction_score += PREDICTION_SIGNAL_WEIGHTS.get("atr_reasonable_daily", 0)
            prediction_details.append("일일 ATR 합리적")

        # --- 최종 예측 결과 구성 ---
        if prediction_score >= PREDICTION_THRESHOLD and potential_buy_info:
            logger.info(f"Next-day buy price prediction for {ticker} (Score: {prediction_score}).")
            predicted_price = potential_buy_info['price']
            range_low = predicted_price - proximity_threshold
            range_high = predicted_price + proximity_threshold

            return {
                'ticker': ticker, 'price_type': potential_buy_info['price_type'],
                'price': predicted_price, 'range_low': range_low, 'range_high': range_high,
                'reason': potential_buy_info.get('reason'), 'score': prediction_score, 'details': prediction_details
            }

        return {}
