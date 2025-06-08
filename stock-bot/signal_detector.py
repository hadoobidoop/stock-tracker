# signal_detector.py

import logging

import pandas as pd

# config에서 PREDICTION_ATR_MULTIPLIER_FOR_RANGE를 임포트
from config import SIGNAL_WEIGHTS, SIGNAL_THRESHOLD, VOLUME_SURGE_FACTOR, PREDICTION_ATR_MULTIPLIER_FOR_RANGE, \
    SIGNAL_ADJUSTMENT_FACTORS_BY_TREND  # SIGNAL_ADJUSTMENT_FACTORS_BY_TREND 추가
from database_setup import TrendType

logger = logging.getLogger(__name__)

# 실시간 신호 감지를 위해 필요한 지표 컬럼들 (calculate_intraday_indicators 함수에 의해 생성될 것들)
# pandas_ta가 컬럼명을 동적으로 생성하므로, 여기서 동적으로 참조하거나, 명시적으로 나열해야 함
# 여기서는 필요한 컬럼들의 접두사를 기반으로 검증 로직을 사용합니다.
REQUIRED_INTRADAY_INDICATOR_PREFIXES = [
    'Open', 'High', 'Low', 'Close', 'Volume',  # OHLCV
    'SMA_', 'RSI_', 'MACD', 'STOCH', 'ADX_',  # 지표 (접두사로 확인)
    'BBL_', 'BBM_', 'BBU_',  # 볼린저 밴드
    'KCLe_', 'KCBe_', 'KCUe_',  # 켈트너 채널 (KCMe_20_2.0 도 포함하도록 추가)
    'Volume_SMA_',  # 거래량 SMA
    'ATR'  # ATR 컬럼 추가 (calculate_intraday_indicators에서 생성될 것으로 가정)
]


def detect_weighted_signals(df_intraday: pd.DataFrame,
                            ticker: str,
                            market_trend: TrendType = TrendType.NEUTRAL,
                            long_term_trend: TrendType = TrendType.NEUTRAL,
                            daily_extra_indicators: dict = None) -> dict:
    """
    1분봉 데이터에 기반한 가중치 복합 매수/매도 신호를 감지합니다.
    시장 추세(market_trend)에 따라 신호 임계값 및 개별 지표 점수를 동적으로 조정합니다.
    일봉 지표(피봇, 피보나치)를 활용하여 지지/저항에서의 반전 신호를 감지합니다.
    ATR 기반 손절매 가격을 계산하여 반환합니다.

    Args:
        df_intraday (pd.DataFrame): 1분봉 OHLCV 및 지표 데이터.
        ticker (str): 주식 티커 심볼.
        market_trend (str): 시장의 전반적인 추세 ('BULLISH', 'BEARISH', 'NEUTRAL').
        daily_extra_indicators (dict): 일봉 데이터에서 계산된 피봇 포인트, 피보나치 되돌림 수준 등.
        long_term_trend:
    Returns:
        dict: 감지된 신호 정보 (type, score, details, stop_loss_price). 신호 없으면 빈 딕셔너리.
    """
    if df_intraday.empty or len(df_intraday) < 2:
        logger.warning(f"Not enough intraday data for signal detection for {ticker}.")
        return {}

    # 필요한 지표 컬럼들이 DataFrame에 존재하는지 확인 (접두사 기반)
    current_cols = df_intraday.columns
    for prefix in REQUIRED_INTRADAY_INDICATOR_PREFIXES:
        if prefix not in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if not any(col.startswith(prefix) for col in current_cols):
                logger.error(f"Missing required indicator '{prefix}...' for {ticker}. Cannot detect signals.")
                return {}
        elif prefix not in current_cols:
            logger.error(f"Missing required OHLCV column '{prefix}' for {ticker}. Cannot detect signals.")
            return {}

    latest_data = df_intraday.iloc[-1]
    prev_data = df_intraday.iloc[-2]

    buy_score = 0
    sell_score = 0
    buy_details = []
    sell_details = []

    # ATR 값 가져오기 (1분봉 데이터에서 계산된 ATR 사용)
    atr_col_name = [col for col in df_intraday.columns if col.startswith('')]
    current_atr = latest_data.get(atr_col_name[0]) if atr_col_name else 0.0
    if pd.isna(current_atr):
        current_atr = 0.0  # NaN일 경우 0으로 처리

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
    # config.py에서 가져오도록 변경
    adjustment_factors = SIGNAL_ADJUSTMENT_FACTORS_BY_TREND.get(market_trend, {})
    trend_follow_buy_adj = adjustment_factors.get("trend_follow_buy_adj", 1.0)
    trend_follow_sell_adj = adjustment_factors.get("trend_follow_sell_adj", 1.0)
    momentum_reversal_adj = adjustment_factors.get("momentum_reversal_adj", 1.0)
    volume_adj = adjustment_factors.get("volume_adj", 1.0)
    bb_kc_adj = adjustment_factors.get("bb_kc_adj", 1.0)
    pivot_fib_adj = adjustment_factors.get("pivot_fib_adj", 1.0)

    logger.debug(
        f"Market trend '{market_trend}' applying adjustments: TF_Buy={trend_follow_buy_adj}, TF_Sell={trend_follow_sell_adj}, Mom_Rev={momentum_reversal_adj}, Vol={volume_adj}, BB_KC={bb_kc_adj}, Pivot_Fib={pivot_fib_adj}")

    # --- 매수 신호 조건 및 가중치 부여 ---

    # 1. SMA 골든 크로스 (5일 SMA > 20일 SMA)
    if prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']:
        sma_cross_buy_score = SIGNAL_WEIGHTS["golden_cross_sma"] * trend_follow_buy_adj
        if latest_data['ADX_14'] < 25:
            sma_cross_buy_score = sma_cross_buy_score * 0.5
            buy_details.append(f"골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += sma_cross_buy_score
        buy_details.append(f"골든 크로스 (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")

    # 2. MACD 골든 크로스 (MACD 선이 시그널 선 상향 돌파)
    if prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data[
        'MACDs_12_26_9']:
        macd_cross_buy_score = SIGNAL_WEIGHTS["macd_cross"] * trend_follow_buy_adj
        if latest_data['ADX_14'] < 25:
            macd_cross_buy_score = macd_cross_buy_score * 0.5
            buy_details.append(f"MACD 골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += macd_cross_buy_score
        buy_details.append(
            f"MACD 골든 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} > Signal:{latest_data['MACDs_12_26_9']:.2f})")

    # --- 혼합 지표 패턴: MACD + 거래량 확인 매수 신호 ---
    if (prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data[
        'MACDs_12_26_9']) and \
            (latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR):
        buy_score += SIGNAL_WEIGHTS["macd_volume_confirm"] * volume_adj
        buy_details.append(
            f"MACD 골든 크로스 & 거래량 급증 확인 (MACD:{latest_data['MACD_12_26_9']:.2f}, Volume:{latest_data['Volume']:,})")
    # --- 새로운 혼합 지표 패턴 끝 ---

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
                    (prev_data['Close'] <= prev_data['BBL_20_2.0'] and latest_data['Close'] > latest_data[
                        'BBL_20_2.0']):
                buy_score += SIGNAL_WEIGHTS["rsi_bb_reversal"] * momentum_reversal_adj
                buy_details.append(
                    f"RSI 과매도 & BB 하단 반등 (RSI:{latest_data['RSI_14']:.2f}, Close:{latest_data['Close']:.2f} vs BBL:{latest_data['BBL_20_2.0']:.2f})")
    # --- 혼합 지표 패턴 끝 ---

    # 5. 스토캐스틱 매수 신호 (%K가 %D를 상향 돌파하고 과매도 구간 벗어날 때)
    if (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHd_14_3_3'] < latest_data['STOCHk_14_3_3'] < 80):
        buy_score += SIGNAL_WEIGHTS["stoch_cross"] * momentum_reversal_adj
        buy_details.append(f"스토캐스틱 매수 (%K:{latest_data['STOCHk_14_3_3']:.2f} > %D:{latest_data['STOCHd_14_3_3']:.2f})")

    # --- 새로운 혼합 지표 패턴: RSI + 스토캐스틱 매수 신호 ---
    if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) and \
            (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] > latest_data[
                'STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
        buy_score += SIGNAL_WEIGHTS["rsi_stoch_confirm"] * momentum_reversal_adj
        buy_details.append(
            f"RSI/Stoch 동시 매수 신호 (RSI:{latest_data['RSI_14']:.2f}, Stoch %K:{latest_data['STOCHk_14_3_3']:.2f})")
    # --- 새로운 혼합 지표 패턴 끝 ---

    # 6. 거래량 증가 (현재 거래량 > 평균 거래량 * VOLUME_SURGE_FACTOR)
    if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
        buy_score += SIGNAL_WEIGHTS["volume_surge"] * volume_adj
        buy_details.append(
            f"거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")

    # 7. 볼린저 밴드/켈트너 채널 스퀴즈 후 확장 (변동성 확장)
    # Keltner Channels 컬럼명 변경 적용
    is_bb_squeezed = (latest_data['BBU_20_2.0'] < latest_data.get('KCUe_20_2.0', 0.0) and
                      latest_data['BBL_20_2.0'] > latest_data.get('KCLe_20_2.0', 0.0))

    if not is_bb_squeezed and latest_data['Close'] > latest_data['BBU_20_2.0'] and prev_data['Close'] < prev_data[
        'BBU_20_2.0']:
        buy_score += SIGNAL_WEIGHTS["bb_squeeze_expansion"] * bb_kc_adj
        buy_details.append(f"볼린저 밴드/켈트너 채널 확장 (상단 돌파)")

    # --- 새로운 혼합 지표 패턴: 지지/저항 + 모멘텀 반전 매수 신호 ---
    if daily_extra_indicators:
        pivot_points = daily_extra_indicators.get('pivot_points', {})
        fib_retracement_levels = daily_extra_indicators.get('fib_retracement', {})

        # ATR을 기반으로 한 근접 임계값 (price_predictor의 로직 재사용)
        # indicator_calculator에서 ATR_14가 생성되므로, 여기서도 ATR 값을 가져와 활용
        # 1분봉 데이터의 ATR을 사용해야 함. daily_extra_indicators에 ATR이 포함되지 않으므로,
        # df_intraday에서 ATR 값을 가져와야 합니다.
        atr_col_name_intraday = [col for col in df_intraday.columns if col.startswith('ATR')]
        current_atr_intraday = latest_data.get(atr_col_name_intraday[0]) if atr_col_name_intraday else 0.0
        if pd.isna(current_atr_intraday): current_atr_intraday = 0.0

        proximity_threshold = current_atr_intraday * PREDICTION_ATR_MULTIPLIER_FOR_RANGE

        # 피봇 S1/S2 근처에서 RSI/Stoch 반전
        if 'S1' in pivot_points and abs(latest_data['Close'] - pivot_points['S1']) <= proximity_threshold:
            if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] >
                     latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                buy_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                buy_details.append(f"Pivot S1 & 모멘텀 반전 (S1:{pivot_points['S1']:.2f}, Close:{latest_data['Close']:.2f})")

        if 'S2' in pivot_points and abs(latest_data['Close'] - pivot_points['S2']) <= proximity_threshold:
            if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] >
                     latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                buy_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                buy_details.append(f"Pivot S2 & 모멘텀 반전 (S2:{pivot_points['S2']:.2f}, Close:{latest_data['Close']:.2f})")

        # 피보나치 38.2%/50%/61.8% 근처에서 RSI/Stoch 반전
        for fib_level_key in ['38.2%', '50.0%', '61.8%']:
            if fib_level_key in fib_retracement_levels and abs(
                    latest_data['Close'] - fib_retracement_levels[fib_level_key]) <= proximity_threshold:
                if (prev_data['RSI_14'] <= 30 < latest_data['RSI_14']) or \
                        (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] >
                         latest_data['STOCHd_14_3_3'] and latest_data['STOCHk_14_3_3'] < 80):
                    buy_score += SIGNAL_WEIGHTS["fib_momentum_reversal"] * pivot_fib_adj
                    buy_details.append(
                        f"Fib {fib_level_key} & 모멘텀 반전 (Fib:{fib_retracement_levels[fib_level_key]:.2f}, Close:{latest_data['Close']:.2f})")
    # --- 새로운 혼합 지표 패턴 끝 ---

    # 8. 캔들스틱 강세 패턴 (TA-Lib 미사용으로 제외)
    # if latest_data.get('Candle_Bullish_Pattern', 0) == 1:
    #     buy_score += SIGNAL_WEIGHTS["candlestick_bullish_pattern"]
    #     buy_details.append("캔들스틱 강세 패턴")

    # --- 매도 신호 조건 및 가중치 부여 ---

    # 1. SMA 데드 크로스 (5일 SMA < 20일 SMA)
    if prev_data['SMA_5'] > prev_data['SMA_20'] and latest_data['SMA_5'] < latest_data['SMA_20']:
        sma_cross_sell_score = SIGNAL_WEIGHTS["golden_cross_sma"] * trend_follow_sell_adj
        if latest_data['ADX_14'] < 25:
            sma_cross_sell_score = sma_cross_sell_score * 0.5
            sell_details.append(f"데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        sell_score += sma_cross_sell_score
        sell_details.append(f"데드 크로스 (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")

    # 2. MACD 데드 크로스 (MACD 선이 시그널 선 하향 돌파)
    if prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] < latest_data[
        'MACDs_12_26_9']:
        macd_cross_sell_score = SIGNAL_WEIGHTS["macd_cross"] * trend_follow_sell_adj
        if latest_data['ADX_14'] < 25:
            macd_cross_sell_score = macd_cross_sell_score * 0.5
            sell_details.append(f"MACD 데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        sell_score += macd_cross_sell_score
        sell_details.append(
            f"MACD 데드 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} < Signal:{latest_data['MACDs_12_26_9']:.2f})")

    # --- 혼합 지표 패턴: MACD + 거래량 확인 매도 신호 ---
    if (prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] < latest_data[
        'MACDs_12_26_9']) and \
            (latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR and latest_data['Close'] <
             prev_data['Close']):
        sell_score += SIGNAL_WEIGHTS["macd_volume_confirm"] * volume_adj
        sell_details.append(
            f"MACD 데드 크로스 & 하락 거래량 급증 확인 (MACD:{latest_data['MACD_12_26_9']:.2f}, Volume:{latest_data['Volume']:,})")
    # --- 새로운 혼합 지표 패턴 끝 ---

    # 3. ADX 강한 하락 추세 (ADX > 25 이고 -DI > +DI)
    if latest_data['ADX_14'] > 25:
        if latest_data.get('DMN_14', 0) > latest_data.get('DMP_14', 0):
            sell_score += SIGNAL_WEIGHTS["adx_strong_trend"] * trend_follow_sell_adj
            sell_details.append(f"ADX 강한 하락 추세 ({latest_data['ADX_14']:.2f})")

    # 4. RSI 과매수 하락 (RSI >= 70 -> RSI < 70)
    if prev_data['RSI_14'] >= 70 > latest_data['RSI_14']:
        sell_score += SIGNAL_WEIGHTS["rsi_bounce_drop"] * momentum_reversal_adj
        sell_details.append(f"RSI 과매수 하락 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")

    # --- 혼합 지표 패턴: RSI + 볼린저 밴드 매도 신호 ---
    if latest_data['RSI_14'] >= 70:
        if latest_data['Close'] >= latest_data['BBU_20_2.0']:
            if prev_data['Close'] < prev_data['BBU_20_2.0'] or \
                    (prev_data['Close'] >= prev_data['BBU_20_2.0'] and latest_data['Close'] < latest_data[
                        'BBU_20_2.0']):
                sell_score += SIGNAL_WEIGHTS["rsi_bb_reversal"] * momentum_reversal_adj
                sell_details.append(
                    f"RSI 과매수 & BB 상단 반등 (RSI:{latest_data['RSI_14']:.2f}, Close:{latest_data['Close']:.2f} vs BBU:{latest_data['BBU_20_2.0']:.2f})")
    # --- 혼합 지표 패턴 끝 ---

    # 5. 스토캐스틱 매도 신호 (%K가 %D를 하향 돌파하고 과매수 구간 벗어날 때)
    if (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHd_14_3_3'] > latest_data['STOCHk_14_3_3'] > 20):
        sell_score += SIGNAL_WEIGHTS["stoch_cross"] * momentum_reversal_adj
        sell_details.append(f"스토캐스틱 매도 (%K:{latest_data['STOCHk_14_3_3']:.2f} < %D:{latest_data['STOCHd_14_3_3']:.2f})")

    # --- 혼합 지표 패턴: RSI + 스토캐스틱 매도 신호 ---
    if (prev_data['RSI_14'] >= 70 > latest_data['RSI_14']) and \
            (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and latest_data[
                'STOCHd_14_3_3'] > latest_data['STOCHk_14_3_3'] > 20):
        sell_score += SIGNAL_WEIGHTS["rsi_stoch_confirm"] * momentum_reversal_adj
        sell_details.append(
            f"RSI/Stoch 동시 매도 신호 (RSI:{latest_data['RSI_14']:.2f}, Stoch %K:{latest_data['STOCHk_14_3_3']:.2f})")
    # --- 새로운 혼합 지표 패턴 끝 ---

    # 6. 거래량 증가 (하락 시 거래량 증가)
    if latest_data['Close'] < prev_data['Close'] and latest_data['Volume'] > latest_data[
        'Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
        sell_score += SIGNAL_WEIGHTS["volume_surge"] * volume_adj
        sell_details.append(
            f"하락 시 거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")

    # 7. 볼린저 밴드/켈트너 채널 스퀴즈 후 확장 (변동성 확장)
    # Keltner Channels 컬럼명 변경 적용
    is_bb_squeezed = (latest_data['BBU_20_2.0'] < latest_data.get('KCUe_20_2.0', 0.0) and
                      latest_data['BBL_20_2.0'] > latest_data.get('KCLe_20_2.0', 0.0))

    if not is_bb_squeezed and latest_data['Close'] < latest_data['BBL_20_2.0'] and prev_data['Close'] > prev_data[
        'BBL_20_2.0']:
        sell_score += SIGNAL_WEIGHTS["bb_squeeze_expansion"] * bb_kc_adj
        sell_details.append(f"볼린저 밴드/켈트너 채널 확장 (하단 돌파)")

    # --- 새로운 혼합 지표 패턴: 지지/저항 + 모멘텀 반전 매도 신호 ---
    if daily_extra_indicators:
        pivot_points = daily_extra_indicators.get('pivot_points', {})
        fib_retracement_levels = daily_extra_indicators.get('fib_retracement', {})

        atr_col_name_intraday = [col for col in df_intraday.columns if col.startswith('ATR')]
        current_atr_intraday = latest_data.get(atr_col_name_intraday[0]) if atr_col_name_intraday else 0.0
        if pd.isna(current_atr_intraday): current_atr_intraday = 0.0

        proximity_threshold = current_atr_intraday * PREDICTION_ATR_MULTIPLIER_FOR_RANGE

        # 피봇 R1/R2 근처에서 RSI/Stoch 반전
        if 'R1' in pivot_points and abs(latest_data['Close'] - pivot_points['R1']) <= proximity_threshold:
            if (prev_data['RSI_14'] >= 70 > latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and latest_data['STOCHd_14_3_3'] >
                     latest_data['STOCHk_14_3_3'] > 20):
                sell_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                sell_details.append(
                    f"Pivot R1 & 모멘텀 반전 (R1:{pivot_points['R1']:.2f}, Close:{latest_data['Close']:.2f})")

        if 'R2' in pivot_points and abs(latest_data['Close'] - pivot_points['R2']) <= proximity_threshold:
            if (prev_data['RSI_14'] >= 70 > latest_data['RSI_14']) or \
                    (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and latest_data['STOCHd_14_3_3'] >
                     latest_data['STOCHk_14_3_3'] > 20):
                sell_score += SIGNAL_WEIGHTS["pivot_momentum_reversal"] * pivot_fib_adj
                sell_details.append(
                    f"Pivot R2 & 모멘텀 반전 (R2:{pivot_points['R2']:.2f}, Close:{latest_data['Close']:.2f})")

        # 피보나치 38.2%/50%/61.8% 근처에서 RSI/Stoch 반전
        for fib_level_key in ['38.2%', '50.0%', '61.8%']:
            if fib_level_key in fib_retracement_levels and abs(
                    latest_data['Close'] - fib_retracement_levels[fib_level_key]) <= proximity_threshold:
                if (prev_data['RSI_14'] >= 70 > latest_data['RSI_14']) or \
                        (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and latest_data['STOCHd_14_3_3'] >
                         latest_data['STOCHk_14_3_3'] > 20):
                    sell_score += SIGNAL_WEIGHTS["fib_momentum_reversal"] * pivot_fib_adj
                    sell_details.append(
                        f"Fib {fib_level_key} & 모멘텀 반전 (Fib:{fib_retracement_levels[fib_level_key]:.2f}, Close:{latest_data['Close']:.2f})")
    # --- 새로운 혼합 지표 패턴 끝 ---

    strong_buy_signal_detected = buy_score >= SIGNAL_THRESHOLD and buy_score > sell_score
    strong_sell_signal_detected = sell_score >= SIGNAL_THRESHOLD and sell_score > buy_score

    # --- 최종 신호 판단 ---
    final_signal = {}

    if strong_buy_signal_detected and long_term_trend == TrendType.BULLISH:
        logger.info(f"BUY SIGNAL CONFIRMED for {ticker} (Score: {buy_score}).")

        # ATR 값 안전하게 가져오기
        atr_col = next((col for col in df_intraday.columns if col.startswith('ATR_')), None)
        current_atr = latest_data.get(atr_col, 0.0) if atr_col else 0.0

        # 손절매 가격 계산 (기존 로직 + 안정성 강화)
        stop_loss_price = None
        if pd.notna(current_atr) and current_atr > 0:
            stop_loss_price = latest_data['Close'] - (current_atr * 2)
            # 음수 손절가 방지 로직 유지
            if stop_loss_price < 0:
                stop_loss_price = 0.01

        final_signal = {
            'type': 'BUY',
            'score': int(buy_score),
            'details': buy_details,
            'current_price': latest_data['Close'],
            'timestamp': latest_data.name.to_pydatetime(),
            'stop_loss_price': stop_loss_price
        }

    elif strong_sell_signal_detected and long_term_trend == TrendType.BEARISH:
        logger.info(f"SELL SIGNAL CONFIRMED for {ticker} (Score: {sell_score}).")

        atr_col = next((col for col in df_intraday.columns if col.startswith('ATR_')), None)
        current_atr = latest_data.get(atr_col, 0.0) if atr_col else 0.0

        stop_loss_price = None
        if pd.notna(current_atr) and current_atr > 0:
            stop_loss_price = latest_data['Close'] + (current_atr * 2)

        final_signal = {
            'type': 'SELL',
            'score': int(sell_score),
            'details': sell_details,
            'current_price': latest_data['Close'],
            'timestamp': latest_data.name.to_pydatetime(),
            'stop_loss_price': stop_loss_price
        }

    return final_signal
