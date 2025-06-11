# price_predictor.py

import pandas as pd
import logging
# Changed relative import to absolute import to resolve "attempted relative import with no known parent package" error
from indicator_calculator import calculate_daily_indicators
# Changed relative import to absolute import for config
from config import FIB_LOOKBACK_DAYS, PREDICTION_ATR_MULTIPLIER_FOR_RANGE, PREDICTION_SIGNAL_WEIGHTS, \
    PREDICTION_THRESHOLD
from database_setup import TrendType

logger = logging.getLogger(__name__)


def predict_next_day_buy_price(df_daily_ohlcv: pd.DataFrame, ticker: str, long_term_trend: TrendType = TrendType.NEUTRAL) -> dict:
    """
    전일 OHLCV 데이터를 기반으로 다음 날의 잠재적 매수 가격을 예측합니다.
    PREDICTION_SIGNAL_WEIGHTS와 PREDICTION_THRESHOLD를 사용하여 예측 점수를 계산합니다.

    Args:
        df_daily_ohlcv (pd.DataFrame): 과거 일봉 OHLCV 데이터 (최근 데이터 포함).\n        ticker (str): 주식 티커 심볼.

    Returns:
        dict: 예측된 매수 가격 정보와 이유, 점수.
              예: {'price_type': 'Pivot S1', 'price': 123.45, 'range_low': 123.00, 'range_high': 123.90, 'reason': 'Close near S1', 'score': 15}
              예측이 불가능하거나 점수가 낮으면 빈 딕셔너리 반환.
    """
    # --- [핵심 수정] ---
    # 함수 시작 부분에 방어 코드 추가
    if long_term_trend == TrendType.BEARISH:
        logger.debug(f"Prediction for {ticker} aborted as long-term trend is BEARISH.")
        return {}
    # --- [핵심 수정 끝] ---

    if df_daily_ohlcv.empty or len(df_daily_ohlcv) < max(FIB_LOOKBACK_DAYS, 2):
        logger.warning(
            f"Not enough daily data to predict next day buy price for {ticker}. Need at least {max(FIB_LOOKBACK_DAYS, 2)} days.")
        return {}

    # 일봉 지표 계산 (df_daily_ohlcv는 이미 충분한 과거 데이터 포함)
    df_with_daily_indicators, daily_extra_indicators = calculate_daily_indicators(df_daily_ohlcv, FIB_LOOKBACK_DAYS)

    if df_with_daily_indicators.empty or not daily_extra_indicators:  # daily_extra_indicators가 비어있을 수도 있음
        logger.warning(f"Failed to calculate daily indicators or extra indicators for {ticker}.")
        return {}

    # 가장 최신 (전일) 데이터 추출
    last_day_data = df_with_daily_indicators.iloc[-1]

    # ATR 값 가져오기 (컬럼명은 동적으로 가져옴, 예: ATR_14)
    atr_col_name = [col for col in df_with_daily_indicators.columns if col.startswith('ATR_')]
    current_atr = last_day_data.get(atr_col_name[0]) if atr_col_name else None

    if pd.isna(current_atr) or current_atr is None:
        logger.warning(
            f"ATR value not available for {ticker}, cannot define price range. Setting ATR to 0 for range calculation.")
        current_atr = 0  # ATR이 없으면 범위 설정 안 함

    # 피봇 포인트와 피보나치 레벨 가져오기
    pivot_points = daily_extra_indicators.get('pivot_points', {})
    fib_retracement_levels = daily_extra_indicators.get('fib_retracement', {})
    last_day_close = last_day_data['Close']

    prediction_score = 0
    prediction_details = []
    potential_buy_info = {}

    # 예측 점수 계산 및 잠재적 매수 가격 결정
    # 우선순위: 피봇 S2 > 피보나치 61.8% > 피봇 S1 > 피보나치 50% > 기타 피보나치

    proximity_threshold = current_atr * PREDICTION_ATR_MULTIPLIER_FOR_RANGE

    # 1. 피봇 S2 근접 확인
    if 'S2' in pivot_points and abs(last_day_close - pivot_points['S2']) <= proximity_threshold:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["pivot_s2_near"]
        prediction_details.append(f"Pivot S2 ({pivot_points['S2']:.2f}) 근접")
        if not potential_buy_info: potential_buy_info = {'price_type': 'Pivot S2', 'price': pivot_points['S2'],
                                                         'reason': f"Close near Pivot S2 ({pivot_points['S2']:.2f})"}

    # 2. 피보나치 61.8% 근접 확인
    if '61.8%' in fib_retracement_levels and abs(
            last_day_close - fib_retracement_levels['61.8%']) <= proximity_threshold:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["fib_618_near"]
        prediction_details.append(f"Fib 61.8% ({fib_retracement_levels['61.8%']:.2f}) 근접")
        if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 61.8%',
                                                         'price': fib_retracement_levels['61.8%'],
                                                         'reason': f"Close near Fib 61.8% ({fib_retracement_levels['61.8%']:.2f})"}

    # 3. 피봇 S1 근접 확인
    if 'S1' in pivot_points and abs(last_day_close - pivot_points['S1']) <= proximity_threshold:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["pivot_s1_near"]
        prediction_details.append(f"Pivot S1 ({pivot_points['S1']:.2f}) 근접")
        if not potential_buy_info: potential_buy_info = {'price_type': 'Pivot S1', 'price': pivot_points['S1'],
                                                         'reason': f"Close near Pivot S1 ({pivot_points['S1']:.2f})"}

    # 4. 피보나치 50.0% 근접 확인
    if '50.0%' in fib_retracement_levels and abs(
            last_day_close - fib_retracement_levels['50.0%']) <= proximity_threshold:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["fib_500_near"]
        prediction_details.append(f"Fib 50.0% ({fib_retracement_levels['50.0%']:.2f}) 근접")
        if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 50.0%',
                                                         'price': fib_retracement_levels['50.0%'],
                                                         'reason': f"Close near Fib 50.0% ({fib_retracement_levels['50.0%']:.2f})"}

    # 5. 피보나치 38.2% 근접 확인
    if '38.2%' in fib_retracement_levels and abs(
            last_day_close - fib_retracement_levels['38.2%']) <= proximity_threshold:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["fib_382_near"]
        prediction_details.append(f"Fib 38.2% ({fib_retracement_levels['38.2%']:.2f}) 근접")
        if not potential_buy_info: potential_buy_info = {'price_type': 'Fibonacci 38.2%',
                                                         'price': fib_retracement_levels['38.2%'],
                                                         'reason': f"Close near Fib 38.2% ({fib_retracement_levels['38.2%']:.2f})"}

    # 6. 일일 RSI 과매도 (RSI 30 이하)
    # pandas_ta의 RSI 컬럼명은 'RSI_14'
    rsi_col_name = [col for col in df_with_daily_indicators.columns if col.startswith('RSI_')]
    if rsi_col_name and last_day_data.get(rsi_col_name[0], 100) <= 30:
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["rsi_oversold_daily"]
        prediction_details.append(f"일일 RSI 과매도 ({last_day_data[rsi_col_name[0]]:.2f})")

    # 7. 일일 ATR 합리적 (변동성이 너무 높지 않을 때)
    # 예를 들어 ATR이 종가의 5% 미만이라고 가정 (이 기준은 조정 가능)
    if current_atr > 0 and (current_atr / last_day_close) < 0.05:  # 종가의 5% 미만
        prediction_score += PREDICTION_SIGNAL_WEIGHTS["atr_reasonable_daily"]
        prediction_details.append(f"일일 ATR 합리적 ({current_atr:.2f} / {last_day_close:.2f})")

    # 8. 강세 캔들 (TA-Lib 없이 구현 어려우므로 점수만 포함)
    # if last_day_data.get('Bullish_Candle_Pattern_Score', 0) > 0: # 가상의 컬럼
    #     prediction_score += PREDICTION_SIGNAL_WEIGHTS["bullish_candle_daily"]
    #     prediction_details.append("일일 강세 캔들 패턴")

    if prediction_score >= PREDICTION_THRESHOLD and potential_buy_info:
        logger.info(f"Next-day buy price prediction for {ticker} (Score: {prediction_score}).")
        # 예상 가격 범위 설정
        predicted_price = potential_buy_info['price']
        range_low = predicted_price - proximity_threshold
        range_high = predicted_price + proximity_threshold

        return {
            'ticker': ticker,
            'price_type': potential_buy_info['price_type'],
            'price': predicted_price,
            'range_low': range_low,
            'range_high': range_high,
            'reason': potential_buy_info.get('reason', '지정된 예측 기준 충족'),  # reason이 없을 경우 기본값 제공
            'score': prediction_score,
            'details': prediction_details
        }
    else:
        logger.info(
            f"No strong next-day buy price prediction found for {ticker} (Score: {prediction_score}) based on threshold {PREDICTION_THRESHOLD}.")
        return {}
