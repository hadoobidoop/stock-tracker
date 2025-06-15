# stock_bot/core/analysis_service.py (최종 검증 완료)
# 역할: 지표 계산, 신호 감지, 가격 예측 등 모든 분석 작업을 총괄하는 서비스.
# 기존 signal_jobs, signal_detector, price_predictor 등의 핵심 로직을 모두 통합합니다.

import logging
import pandas as pd
from typing import Dict, Tuple

# 애플리케이션의 다른 모듈들을 가져옵니다.
from ..database.manager import DatabaseManager
from .data_provider import DataProvider
from ..indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
from ..signals.signal_utils import detect_weighted_signals
from ..price_predictor import predict_next_day_buy_price
from ..config import SIGNAL_THRESHOLD, FIB_LOOKBACK_DAYS

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    데이터를 분석하여 의미 있는 정보(지표, 신호, 예측)를 생성하는 핵심 서비스 클래스.
    """
    def __init__(self, data_provider: DataProvider, db_manager: DatabaseManager):
        """
        생성 시, 다른 서비스(DataProvider, DatabaseManager)를 주입받아 의존성을 해결합니다.
        """
        self.data_provider = data_provider
        self.db_manager = db_manager

    def _get_market_trend(self) -> str:
        """[검증 완료] S&P 500 지수를 기준으로 시장의 전반적인 추세를 판단합니다."""
        try:
            df_market = self.data_provider.get_ohlcv('^GSPC', period="210d", interval='1d')
            if df_market.empty or len(df_market) < 200: return "NEUTRAL"

            df_market['SMA_200'] = df_market['Close'].rolling(window=200).mean()
            if pd.isna(df_market.iloc[-1]['SMA_200']): return "NEUTRAL"

            if df_market.iloc[-1]['Close'] > df_market.iloc[-1]['SMA_200']: return "BULLISH"
            if df_market.iloc[-1]['Close'] < df_market.iloc[-1]['SMA_200']: return "BEARISH"
        except Exception as e:
            logger.error(f"Could not determine market trend: {e}")
        return "NEUTRAL"

    def _get_long_term_trend(self, ticker: str) -> Tuple[str, Dict]:
        """[검증 완료] 개별 종목의 장기 추세(1H)와 관련 값을 판단합니다."""
        trend_values = {}
        try:
            now = pd.Timestamp.now(tz='UTC')
            df_hourly = self.db_manager.get_bulk_resampled_ohlcv_from_db(
                [ticker], now - pd.Timedelta(days=31), now, 'H'
            ).get(ticker)

            if df_hourly is None or df_hourly.empty or len(df_hourly) < 50:
                return "NEUTRAL", {}

            df_hourly['SMA_50'] = df_hourly['Close'].rolling(window=50).mean()
            last_close = df_hourly.iloc[-1]['Close']
            last_sma = df_hourly.iloc[-1]['SMA_50']
            trend_values = {'close': last_close, 'sma': last_sma}

            if pd.isna(last_sma): return "NEUTRAL", trend_values

            if last_close > last_sma: return "BULLISH", trend_values
            if last_close < last_sma: return "BEARISH", trend_values
        except Exception as e:
            logger.error(f"Could not determine long term trend for {ticker}: {e}")
        return "NEUTRAL", trend_values

    def analyze_ticker_for_signals(self, ticker: str, df_intraday: pd.DataFrame) -> Dict:
        """
        [검증 완료] 단일 종목에 대해 실시간 신호 분석을 수행하고 최종 신호 데이터를 구성합니다.
        기존 signal_jobs.py와 signal_detector.py의 핵심 로직을 통합합니다.
        """
        if df_intraday.empty or len(df_intraday) < 60:
            logger.warning(f"Not enough data for {ticker} to perform analysis.")
            return {}

        # 1. 지표 계산 및 저장
        df_with_indicators = calculate_intraday_indicators(df_intraday.copy())
        indicator_cols_to_drop = ['Open', 'High', 'Low', 'Close', 'Volume', 'Ticker', 'Interval']
        df_only_indicators = df_with_indicators.drop(columns=indicator_cols_to_drop, errors='ignore')
        self.db_manager.save_technical_indicators(df_only_indicators, ticker, '1m')

        # 2. 분석 컨텍스트 준비 (기존 signal_jobs.py 로직)
        market_trend = self._get_market_trend()
        long_term_trend, trend_values = self._get_long_term_trend(ticker)

        df_daily = self.data_provider.get_ohlcv(ticker, period=f"{FIB_LOOKBACK_DAYS+10}d", interval="1d")
        _, daily_extras = calculate_daily_indicators(df_daily, FIB_LOOKBACK_DAYS) if not df_daily.empty else ({}, {})

        # 3. 가중치 신호 탐지 (기존 signal_utils.py 호출)
        buy_score, sell_score, details = detect_weighted_signals(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
        )

        # 4. 최종 신호 결정 및 데이터 구성 (기존 signal_detector.py 로직)
        strong_buy = buy_score >= SIGNAL_THRESHOLD and buy_score > sell_score
        strong_sell = sell_score >= SIGNAL_THRESHOLD and sell_score > buy_score

        final_signal = {}
        latest_data = df_with_indicators.iloc[-1]

        if strong_buy:
            final_signal = self._build_final_signal_dict('BUY', ticker, buy_score, details, latest_data, trend_values, market_trend, long_term_trend)
        elif strong_sell:
            final_signal = self._build_final_signal_dict('SELL', ticker, sell_score, details, latest_data, trend_values, market_trend, long_term_trend)

        return final_signal

    def _build_final_signal_dict(self, sig_type, ticker, score, details, latest_data, trend_values, market_trend, long_term_trend) -> Dict:
        """[신규] 최종 신호 딕셔너리를 생성하는 헬퍼 메소드 (코드 중복 방지)"""
        logger.info(f"{sig_type} SIGNAL CONFIRMED for {ticker} (Score: {score}).")

        atr_col = next((col for col in latest_data.index if 'ATR' in col), None)
        current_atr = latest_data.get(atr_col, 0.0)
        stop_loss = None

        if pd.notna(current_atr) and current_atr > 0:
            if sig_type == 'BUY':
                stop_loss = latest_data['Close'] - (current_atr * 2)
                if stop_loss < 0: stop_loss = 0.01
            else: # SELL
                stop_loss = latest_data['Close'] + (current_atr * 2)

        return {
            'type': sig_type,
            'ticker': ticker,
            'score': int(score),
            'details': details,
            'current_price': latest_data['Close'],
            'timestamp': latest_data.name.to_pydatetime(),
            'stop_loss_price': stop_loss,
            'market_trend': market_trend,
            'long_term_trend': long_term_trend,
            'trend_ref_close': trend_values.get('close'),
            'trend_ref_value': trend_values.get('sma')
        }

    def predict_next_day_buy_price(self, ticker: str) -> Dict:
        """[검증 완료] 다음 날의 잠재적 매수 가격을 예측합니다."""
        df_daily = self.data_provider.get_ohlcv(ticker, period="1y", interval="1d")
        if df_daily.empty:
            return {}

        long_term_trend, _ = self._get_long_term_trend(ticker)
        if long_term_trend == "BEARISH":
            logger.info(f"Skipping prediction for {ticker} due to BEARISH long-term trend.")
            return {}

        prediction_result = predict_next_day_buy_price(df_daily.copy(), ticker, long_term_trend)

        # 예측 결과가 있을 경우, 추가 정보 주입
        if prediction_result:
            prediction_result['prediction_date_utc'] = (pd.Timestamp.now(tz='UTC') + pd.Timedelta(days=1)).date()
            prediction_result['generated_at_utc'] = pd.Timestamp.now(tz='UTC')
            prediction_result['prev_day_close'] = df_daily.iloc[-1]['Close']

        return prediction_result
