import logging
import pandas as pd

from ..config import SIGNAL_WEIGHTS, VOLUME_SURGE_FACTOR, PREDICTION_ATR_MULTIPLIER_FOR_RANGE, SIGNAL_THRESHOLD, \
    SIGNAL_ADJUSTMENT_FACTORS_BY_TREND
from ..database_setup import TrendType

logger = logging.getLogger(__name__)

def detect_buy_signals(df_intraday: pd.DataFrame, ticker: str, market_trend: TrendType,
                      long_term_trend: TrendType, daily_extra_indicators: dict = None) -> tuple[float, list]:
    """
    매수 신호를 감지하고 점수를 계산합니다.
    
    Args:
        df_intraday (pd.DataFrame): 1분봉 OHLCV 및 지표 데이터
        ticker (str): 주식 티커 심볼
        market_trend (TrendType): 시장의 전반적인 추세
        long_term_trend (TrendType): 종목의 장기 추세
        daily_extra_indicators (dict): 일봉 데이터에서 계산된 피봇 포인트, 피보나치 되돌림 수준 등
        
    Returns:
        tuple[float, list]: (매수 점수, 매수 신호 상세 정보 리스트)
    """
    if df_intraday.empty or len(df_intraday) < 2:
        logger.warning(f"Not enough intraday data for buy signal detection for {ticker}.")
        return 0.0, []

    latest_data = df_intraday.iloc[-1]
    prev_data = df_intraday.iloc[-2]

    buy_score = 0
    buy_details = []

    # --- 시장 추세에 따른 신호 임계값 동적 조정 ---
    adjusted_signal_threshold = SIGNAL_THRESHOLD
    if market_trend == "BEARISH":
        adjusted_signal_threshold = SIGNAL_THRESHOLD * 1.2
        logger.debug(
            f"Adjusting BUY signal threshold for {ticker} in BEARISH market to {adjusted_signal_threshold:.2f}.")
    elif market_trend == "BULLISH":
        adjusted_signal_threshold = SIGNAL_THRESHOLD * 0.8
        logger.debug(
            f"Adjusting BUY signal threshold for {ticker} in BULLISH market to {adjusted_signal_threshold:.2f}.")

    # --- 개별 지표 점수 조정 계수 (시장 추세에 따라) ---
    adjustment_factors = SIGNAL_ADJUSTMENT_FACTORS_BY_TREND.get(market_trend, {})
    trend_follow_buy_adj = adjustment_factors.get("trend_follow_buy_adj", 1.0)
    momentum_reversal_adj = adjustment_factors.get("momentum_reversal_adj", 1.0)
    volume_adj = adjustment_factors.get("volume_adj", 1.0)
    bb_kc_adj = adjustment_factors.get("bb_kc_adj", 1.0)
    pivot_fib_adj = adjustment_factors.get("pivot_fib_adj", 1.0)

    # 1. SMA 골든 크로스 (5일 SMA > 20일 SMA)
    if prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']:
        sma_cross_buy_score = SIGNAL_WEIGHTS["golden_cross_sma"] * trend_follow_buy_adj
        if latest_data['ADX_14'] < 25:
            sma_cross_buy_score = sma_cross_buy_score * 0.5
            buy_details.append(f"골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += sma_cross_buy_score
        buy_details.append(f"골든 크로스 (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")

    # 2. MACD 골든 크로스 (MACD 선이 시그널 선 상향 돌파)
    if prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']:
        macd_cross_buy_score = SIGNAL_WEIGHTS["macd_cross"] * trend_follow_buy_adj
        if latest_data['ADX_14'] < 25:
            macd_cross_buy_score = macd_cross_buy_score * 0.5
            buy_details.append(f"MACD 골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += macd_cross_buy_score
        buy_details.append(f"MACD 골든 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} > Signal:{latest_data['MACDs_12_26_9']:.2f})")

    # --- 혼합 지표 패턴: MACD + 거래량 확인 매수 신호 ---
    if (prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']) and \
            (latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR):
        buy_score += SIGNAL_WEIGHTS["macd_volume_confirm"] * volume_adj
        buy_details.append(f"MACD 골든 크로스 & 거래량 급증 확인 (MACD:{latest_data['MACD_12_26_9']:.2f}, Volume:{latest_data['Volume']:,})")

    # 3. ADX 강한 상승 추세 (ADX > 25 이고 +DI > -DI)
    if latest_data['ADX_14'] > 25:
        if latest_data.get('DMP_14', 0) > latest_data.get('DMN_14', 0):
            buy_score += SIGNAL_WEIGHTS["adx_strong_trend"] * trend_follow_buy_adj
            buy_details.append(f"ADX 강한 상승 추세 ({latest_data['ADX_14']:.2f})")

    # 4. RSI 과매도 탈출 (RSI <= 30 -> RSI > 30)
    if prev_data['RSI_14'] <= 30 < latest_data['RSI_14']:
        buy_score += SIGNAL_WEIGHTS["rsi_bounce_drop"] * momentum_reversal_adj
        buy_details.append(f"RSI 과매도 탈출 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")

    # --- 혼합 지표 패턴: RSI + 볼린저 밴드 매수 신호 ---
    if latest_data['RSI_14'] <= 30:
        if latest_data['Close'] <= latest_data['BBL_20_2.0']:
            if prev_data['Close'] > prev_data['BBL_20_2.0'] or \
                    (prev_data['Close'] <= prev_data['BBL_20_2.0'] and latest_data['Close'] > latest_data['BBL_20_2.0']):
                buy_score += SIGNAL_WEIGHTS["rsi_bb_reversal"] * momentum_reversal_adj
                buy_details.append(f"RSI 과매도 & BB 하단 반등 (RSI:{latest_data['RSI_14']:.2f}, Close:{latest_data['Close']:.2f} vs BBL:{latest_data['BBL_20_2.0']:.2f})")

    # 5. 스토캐스틱 매수 신호 (%K가 %D를 상향 돌파하고 과매도 구간 벗어날 때)
    if (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHd_14_3_3'] < latest_data['STOCHk_14_3_3'] < 80):
        buy_score += SIGNAL_WEIGHTS["stoch_cross"] * momentum_reversal_adj
        buy_details.append(f"스토캐스틱 매수 (%K:{latest_data['STOCHk_14_3_3']:.2f} > %D:{latest_data['STOCHd_14_3_3']:.2f})")

    # --- 새로운 혼합 지표 패턴: RSI + 스토캐스틱 매수 신호 ---
    if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) and \
            (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
        buy_score += SIGNAL_WEIGHTS["rsi_stoch_confirm"] * momentum_reversal_adj
        buy_details.append(f"RSI/Stoch 동시 매수 신호 (RSI:{latest_data['RSI_14']:.2f}, Stoch %K:{latest_data['STOCHk_14_3_3']:.2f})")

    # 6. 거래량 증가 (현재 거래량 > 평균 거래량 * VOLUME_SURGE_FACTOR)
    if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
        buy_score += SIGNAL_WEIGHTS["volume_surge"] * volume_adj
        buy_details.append(f"거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")

    # 7. 볼린저 밴드/켈트너 채널 스퀴즈 후 확장 (변동성 확장)
    is_bb_squeezed = (latest_data['BBU_20_2.0'] < latest_data.get('KCUe_20_2.0', 0.0) and
                      latest_data['BBL_20_2.0'] > latest_data.get('KCLe_20_2.0', 0.0))

    if not is_bb_squeezed and latest_data['Close'] > latest_data['BBU_20_2.0'] and prev_data['Close'] < prev_data['BBU_20_2.0']:
        buy_score += SIGNAL_WEIGHTS["bb_squeeze_expansion"] * bb_kc_adj
        buy_details.append(f"볼린저 밴드/켈트너 채널 확장 (상단 돌파)")

    # --- 새로운 혼합 지표 패턴: 지지/저항 + 모멘텀 반전 매수 신호 ---
    if daily_extra_indicators:
        pivot_points = daily_extra_indicators.get('pivot_points', {})
        fib_retracement_levels = daily_extra_indicators.get('fib_retracement', {})

        # ATR을 기반으로 한 근접 임계값
        atr_col_name_intraday = [col for col in df_intraday.columns if col.startswith('ATR')]
        current_atr_intraday = latest_data.get(atr_col_name_intraday[0]) if atr_col_name_intraday else 0.0
        if pd.isna(current_atr_intraday): current_atr_intraday = 0.0

        proximity_threshold = current_atr_intraday * PREDICTION_ATR_MULTIPLIER_FOR_RANGE

        # 피봇 S1/S2 근처에서 RSI/Stoch 반전
        if 'S1' in pivot_points and abs(latest_data['Close'] - pivot_points['S1']) <= proximity_threshold:
            if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                buy_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                buy_details.append(f"Pivot S1 & 모멘텀 반전 (S1:{pivot_points['S1']:.2f}, Close:{latest_data['Close']:.2f})")

        if 'S2' in pivot_points and abs(latest_data['Close'] - pivot_points['S2']) <= proximity_threshold:
            if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                buy_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                buy_details.append(f"Pivot S2 & 모멘텀 반전 (S2:{pivot_points['S2']:.2f}, Close:{latest_data['Close']:.2f})")

        # 피보나치 38.2%/50%/61.8% 근처에서 RSI/Stoch 반전
        for fib_level_key in ['38.2%', '50.0%', '61.8%']:
            if fib_level_key in fib_retracement_levels and abs(latest_data['Close'] - fib_retracement_levels[fib_level_key]) <= proximity_threshold:
                if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                        (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] > latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                    buy_score += SIGNAL_WEIGHTS["fib_momentum_reversal"] * pivot_fib_adj
                    buy_details.append(f"Fib {fib_level_key} & 모멘텀 반전 (Fib:{fib_retracement_levels[fib_level_key]:.2f}, Close:{latest_data['Close']:.2f})")

    return buy_score, buy_details 