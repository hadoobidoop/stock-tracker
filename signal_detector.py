# signal_detector.py

import pandas as pd
import logging
from config import SIGNAL_WEIGHTS, SIGNAL_THRESHOLD, VOLUME_SURGE_FACTOR

logger = logging.getLogger(__name__)

# 실시간 신호 감지를 위해 필요한 지표 컬럼들 (calculate_intraday_indicators 함수에 의해 생성될 것들)
# pandas_ta가 컬럼명을 동적으로 생성하므로, 여기서 동적으로 참조하거나, 명시적으로 나열해야 함
# 여기서는 필요한 컬럼들의 접두사를 기반으로 검증 로직을 사용합니다.
REQUIRED_INTRADAY_INDICATOR_PREFIXES = [
    'Open', 'High', 'Low', 'Close', 'Volume', # OHLCV
    'SMA_', 'RSI_', 'MACD', 'STOCH', 'ADX_',  # 지표 (접두사로 확인)
    'BBL_', 'BBM_', 'BBU_', # 볼린저 밴드
    'KCLe_', 'KCUe_', # 켈트너 채널 (KCMe_는 생성되지 않으므로 제거)
    'Volume_SMA_' # 거래량 SMA
]

def detect_weighted_signals(df_intraday: pd.DataFrame, ticker: str) -> dict:
    """
    1분봉 데이터에 기반한 가중치 복합 매수/매도 신호를 감지합니다.

    Args:
        df_intraday (pd.DataFrame): 1분봉 OHLCV 및 지표 데이터.
        ticker (str): 주식 티커 심볼.

    Returns:
        dict: 감지된 신호 정보 (type, score, details). 신호 없으면 빈 딕셔너리.
    """
    if df_intraday.empty or len(df_intraday) < 2:
        logger.warning(f"Not enough intraday data for signal detection for {ticker}.")
        return {}

    # 필요한 지표 컬럼들이 DataFrame에 존재하는지 확인 (접두사 기반)
    current_cols = df_intraday.columns
    # 모든 필수 접두사가 최소 하나의 매칭되는 컬럼을 가지는지 확인
    for prefix in REQUIRED_INTRADAY_INDICATOR_PREFIXES:
        if prefix not in ['Open', 'High', 'Low', 'Close', 'Volume']: # OHLCV는 정확히 일치해야 함
            if not any(col.startswith(prefix) for col in current_cols):
                logger.error(f"Missing required indicator '{prefix}...' for {ticker}. Cannot detect signals.")
                return {}
        elif prefix not in current_cols: # OHLCV 컬럼 정확히 확인
            logger.error(f"Missing required OHLCV column '{prefix}' for {ticker}. Cannot detect signals.")
            return {}

    # 가장 최신 데이터와 이전 데이터
    latest_data = df_intraday.iloc[-1]
    prev_data = df_intraday.iloc[-2]

    buy_score = 0
    sell_score = 0
    buy_details = []
    sell_details = []

    # --- 매수 신호 조건 및 가중치 부여 ---

    # 1. SMA 골든 크로스 (5일 SMA > 20일 SMA)
    if prev_data['SMA_5'] < prev_data['SMA_20'] and latest_data['SMA_5'] > latest_data['SMA_20']:
        sma_cross_buy_score = SIGNAL_WEIGHTS["golden_cross_sma"]
        if latest_data['ADX_14'] < 25: # ADX가 낮으면 추세 신호 가중치 감소
            sma_cross_buy_score = sma_cross_buy_score * 0.5
            buy_details.append(f"골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += sma_cross_buy_score
        buy_details.append(f"골든 크로스 (SMA 5:{latest_data['SMA_5']:.2f} > 20:{latest_data['SMA_20']:.2f})")


    # 2. MACD 골든 크로스 (MACD 선이 시그널 선 상향 돌파)
    if prev_data['MACD_12_26_9'] < prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] > latest_data['MACDs_12_26_9']:
        macd_cross_buy_score = SIGNAL_WEIGHTS["macd_cross"]
        if latest_data['ADX_14'] < 25: # ADX가 낮으면 모멘텀 신호 가중치 감소
            macd_cross_buy_score = macd_cross_buy_score * 0.5
            buy_details.append(f"MACD 골든 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        buy_score += macd_cross_buy_score
        buy_details.append(f"MACD 골든 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} > Signal:{latest_data['MACDs_12_26_9']:.2f})")


    # 3. ADX 강한 상승 추세 (ADX > 25 이고 +DI > -DI)
    if latest_data['ADX_14'] > 25:
        if latest_data.get('DMP_14', 0) > latest_data.get('DMN_14', 0): # DMP_14: +DI, DMN_14: -DI
            buy_score += SIGNAL_WEIGHTS["adx_strong_trend"]
            buy_details.append(f"ADX 강한 상승 추세 ({latest_data['ADX_14']:.2f})")

    # 4. RSI 과매도 탈출 (RSI <= 30 -> RSI > 30)
    if prev_data['RSI_14'] <= 30 < latest_data['RSI_14']:
        buy_score += SIGNAL_WEIGHTS["rsi_bounce_drop"]
        buy_details.append(f"RSI 과매도 탈출 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")

    # 5. 스토캐스틱 매수 신호 (%K가 %D를 상향 돌파하고 과매도 구간 벗어날 때)
    if (prev_data['STOCHk_14_3_3'] < prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHd_14_3_3'] < latest_data['STOCHk_14_3_3'] < 80): # 과매수 구간 진입 직전 (안전한 매수)
        buy_score += SIGNAL_WEIGHTS["stoch_cross"]
        buy_details.append(f"스토캐스틱 매수 (%K:{latest_data['STOCHk_14_3_3']:.2f} > %D:{latest_data['STOCHd_14_3_3']:.2f})")

    # 6. 거래량 증가 (현재 거래량 > 평균 거래량 * VOLUME_SURGE_FACTOR)
    if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
        buy_score += SIGNAL_WEIGHTS["volume_surge"]
        buy_details.append(f"거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")

    # 7. 볼린저 밴드/켈트너 채널 스퀴즈 후 확장 (변동성 확장)
    # 스퀴즈: 볼린저 밴드가 켈트너 채널 안에 있을 때 (BBU < KCU and BBL > KCL)
    # 확장: 스퀴즈 상태에서 벗어나 밴드가 벌어질 때
    # 간소화된 스퀴즈 후 확장을 위해서는 과거 여러 기간을 봐야 하지만, 여기서는 단순화
    is_bb_squeezed = (latest_data['BBU_20_2.0'] < latest_data['KCUe_20_2'] and # KCUe_20_2로 변경
                      latest_data['BBL_20_2.0'] > latest_data['KCLe_20_2']) # KCLe_20_2로 변경

    if not is_bb_squeezed and latest_data['Close'] > latest_data['BBU_20_2.0'] and prev_data['Close'] < prev_data['BBU_20_2.0']:
        buy_score += SIGNAL_WEIGHTS["bb_squeeze_expansion"]
        buy_details.append(f"볼린저 밴드/켈트너 채널 확장 (상단 돌파)")


    # 8. 캔들스틱 강세 패턴 (TA-Lib 미사용으로 제외)
    # if latest_data.get('Candle_Bullish_Pattern', 0) == 1:
    #     buy_score += SIGNAL_WEIGHTS["candlestick_bullish_pattern"]
    #     buy_details.append("캔들스틱 강세 패턴")


    # --- 매도 신호 조건 및 가중치 부여 ---

    # 1. SMA 데드 크로스 (5일 SMA < 20일 SMA)
    if prev_data['SMA_5'] > prev_data['SMA_20'] and latest_data['SMA_5'] < latest_data['SMA_20']:
        sma_cross_sell_score = SIGNAL_WEIGHTS["golden_cross_sma"]
        if latest_data['ADX_14'] < 25: # ADX가 낮으면 추세 신호 가중치 감소
            sma_cross_sell_score = sma_cross_sell_score * 0.5
            sell_details.append(f"데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        sell_score += sma_cross_sell_score
        sell_details.append(f"데드 크로스 (SMA 5:{latest_data['SMA_5']:.2f} < 20:{latest_data['SMA_20']:.2f})")

    # 2. MACD 데드 크로스 (MACD 선이 시그널 선 하향 돌파)
    if prev_data['MACD_12_26_9'] > prev_data['MACDs_12_26_9'] and latest_data['MACD_12_26_9'] < latest_data['MACDs_12_26_9']:
        macd_cross_sell_score = SIGNAL_WEIGHTS["macd_cross"]
        if latest_data['ADX_14'] < 25: # ADX가 낮으면 모멘텀 신호 가중치 감소
            macd_cross_sell_score = macd_cross_sell_score * 0.5
            sell_details.append(f"MACD 데드 크로스 (ADX 약세로 가중치 감소: {latest_data['ADX_14']:.2f})")
        sell_score += macd_cross_sell_score
        sell_details.append(f"MACD 데드 크로스 (MACD:{latest_data['MACD_12_26_9']:.2f} < Signal:{latest_data['MACDs_12_26_9']:.2f})")

    # 3. ADX 강한 하락 추세 (ADX > 25 이고 -DI > +DI)
    if latest_data['ADX_14'] > 25:
        if latest_data.get('DMN_14', 0) > latest_data.get('DMP_14', 0):
            sell_score += SIGNAL_WEIGHTS["adx_strong_trend"]
            sell_details.append(f"ADX 강한 하락 추세 ({latest_data['ADX_14']:.2f})")

    # 4. RSI 과매수 하락 (RSI >= 70 -> RSI < 70)
    if prev_data['RSI_14'] >= 70 > latest_data['RSI_14']:
        sell_score += SIGNAL_WEIGHTS["rsi_bounce_drop"]
        sell_details.append(f"RSI 과매수 하락 ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")

    # 5. 스토캐스틱 매도 신호 (%K가 %D를 하향 돌파하고 과매수 구간 벗어날 때)
    if (prev_data['STOCHk_14_3_3'] > prev_data['STOCHd_14_3_3'] and
            latest_data['STOCHd_14_3_3'] > latest_data['STOCHk_14_3_3'] > 20): # 과매도 구간 진입 직전 (안전한 매도)
        sell_score += SIGNAL_WEIGHTS["stoch_cross"]
        sell_details.append(f"스토캐스틱 매도 (%K:{latest_data['STOCHk_14_3_3']:.2f} < %D:{latest_data['STOCHd_14_3_3']:.2f})")

    # 6. 거래량 증가 (하락 시 거래량 증가)
    if latest_data['Close'] < prev_data['Close'] and latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
        sell_score += SIGNAL_WEIGHTS["volume_surge"]
        sell_details.append(f"하락 시 거래량 급증 (현재:{latest_data['Volume']} > 평균:{latest_data['Volume_SMA_20']:.0f} * {VOLUME_SURGE_FACTOR})")

    # 7. 볼린저 밴드/켈트너 채널 스퀴즈 후 확장 (변동성 확장)
    # 이전 스퀴즈 상태에서 현재 하단 밴드(BBL)를 하향 돌파할 때
    is_bb_squeezed = (latest_data['BBU_20_2.0'] < latest_data['KCUe_20_2'] and # KCUe_20_2로 변경
                      latest_data['BBL_20_2.0'] > latest_data['KCLe_20_2']) # KCLe_20_2로 변경

    if not is_bb_squeezed and latest_data['Close'] < latest_data['BBL_20_2.0'] and prev_data['Close'] > prev_data['BBL_20_2.0']:
        sell_score += SIGNAL_WEIGHTS["bb_squeeze_expansion"]
        sell_details.append(f"볼린저 밴드/켈트너 채널 확장 (하단 돌파)")

    # 8. 캔들스틱 약세 패턴 (TA-Lib 미사용으로 제외)
    # if latest_data.get('Candle_Bearish_Pattern', 0) == -1:
    #     sell_score += SIGNAL_WEIGHTS["candlestick_bearish_pattern"]
    #     sell_details.append("캔들스틱 약세 패턴")


    # --- 최종 신호 판단 ---
    # Buy 신호 점수가 Threshold 이상이고, Sell 신호 점수보다 높을 때
    if buy_score >= SIGNAL_THRESHOLD and buy_score > sell_score:
        logger.info(f"Strong BUY signal detected for {ticker} (Score: {buy_score}).")
        return {
            'type': 'BUY',
            'score': buy_score,
            'details': buy_details,
            'current_price': latest_data['Close'],
            'timestamp': latest_data.name.strftime('%Y-%m-%d %H:%M')
        }
    # Sell 신호 점수가 Threshold 이상이고, Buy 신호 점수보다 높을 때
    elif sell_score >= SIGNAL_THRESHOLD and sell_score > buy_score:
        logger.info(f"Strong SELL signal detected for {ticker} (Score: {sell_score}).")
        return {
            'type': 'SELL',
            'score': sell_score,
            'details': sell_details,
            'current_price': latest_data['Close'],
            'timestamp': latest_data.name.strftime('%Y-%m-%d %H:%M')
        }
    else:
        # logger.debug(f"No strong signal for {ticker}. Buy Score: {buy_score}, Sell Score: {sell_score}")
        return {}
