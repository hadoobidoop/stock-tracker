import logging
import pandas as pd

from ..config import SIGNAL_THRESHOLD
from ..database_setup import TrendType
from .buy_signals import detect_buy_signals
from .sell_signals import detect_sell_signals

logger = logging.getLogger(__name__)

def detect_weighted_signals(df_intraday: pd.DataFrame, ticker: str, market_trend: TrendType,
                          long_term_trend: TrendType, daily_extra_indicators: dict = None) -> tuple[float, float, list]:
    """
    매수/매도 신호를 감지하고 가중치를 적용하여 점수를 계산합니다.
    
    Args:
        df_intraday (pd.DataFrame): 1분봉 OHLCV 및 지표 데이터
        ticker (str): 주식 티커 심볼
        market_trend (TrendType): 시장의 전반적인 추세
        long_term_trend (TrendType): 종목의 장기 추세
        daily_extra_indicators (dict): 일봉 데이터에서 계산된 피봇 포인트, 피보나치 되돌림 수준 등
        
    Returns:
        tuple[float, float, list]: (매수 점수, 매도 점수, 신호 상세 정보 리스트)
    """
    if df_intraday.empty or len(df_intraday) < 2:
        logger.warning(f"Not enough intraday data for signal detection for {ticker}.")
        return 0.0, 0.0, []

    # 매수/매도 신호 감지
    buy_score, buy_details = detect_buy_signals(df_intraday, ticker, market_trend, long_term_trend, daily_extra_indicators)
    sell_score, sell_details = detect_sell_signals(df_intraday, ticker, market_trend, long_term_trend, daily_extra_indicators)

    # 시장 추세에 따른 신호 임계값 동적 조정
    adjusted_signal_threshold = SIGNAL_THRESHOLD
    if market_trend == "BULLISH":
        adjusted_signal_threshold = SIGNAL_THRESHOLD * 0.8
        logger.debug(f"Adjusting signal threshold for {ticker} in BULLISH market to {adjusted_signal_threshold:.2f}.")
    elif market_trend == "BEARISH":
        adjusted_signal_threshold = SIGNAL_THRESHOLD * 1.2
        logger.debug(f"Adjusting signal threshold for {ticker} in BEARISH market to {adjusted_signal_threshold:.2f}.")

    # 장기 추세에 따른 신호 점수 조정
    if long_term_trend == "BULLISH":
        buy_score *= 1.2
        sell_score *= 0.8
        logger.debug(f"Adjusting signal scores for {ticker} in BULLISH long-term trend.")
    elif long_term_trend == "BEARISH":
        buy_score *= 0.8
        sell_score *= 1.2
        logger.debug(f"Adjusting signal scores for {ticker} in BEARISH long-term trend.")

    # 신호 상세 정보 리스트 생성
    signal_details = []
    if buy_score > adjusted_signal_threshold:
        signal_details.extend([f"매수 신호: {detail}" for detail in buy_details])
    if sell_score > adjusted_signal_threshold:
        signal_details.extend([f"매도 신호: {detail}" for detail in sell_details])

    return buy_score, sell_score, signal_details 