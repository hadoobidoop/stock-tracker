import pandas as pd
import yfinance as yf
from datetime import datetime

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from indicator_calculator import calculate_intraday_indicators
from config import SIGNAL_WEIGHTS, SIGNAL_THRESHOLD, VOLUME_SURGE_FACTOR

# --- 1. 데이터 로딩 함수 (변경 없음) ---
def load_data_for_backtest(ticker: str, start_date: str, end_date: str, timeframe: str = '60T') -> pd.DataFrame:
    print(f"Loading data for {ticker} directly from Yahoo Finance from {start_date} to {end_date}...")
    yf_interval = timeframe.replace('T', 'm')
    df = yf.download(ticker, start=start_date, end=end_date, interval=yf_interval, progress=False, auto_adjust=False)

    if df.empty:
        print("No data found for the given period from Yahoo Finance.")
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }, inplace=True)

    df.dropna(inplace=True)
    print("Data loading complete.")
    return df


# --- 2. 백테스팅 전략 정의 (init 함수 수정) ---
class SwingTradingStrategy(Strategy):
    sma_short = 5
    sma_long = 20
    rsi_period = 14
    adx_period = 14
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    signal_threshold = SIGNAL_THRESHOLD

    def init(self):
        """
        백테스팅 시작 전 한 번만 호출되는 초기화 함수.
        여기서 모든 기술적 지표를 미리 계산합니다.
        """
        df_with_indicators = calculate_intraday_indicators(self.data.df.copy())

        # --- [핵심 수정] ---
        # .values 를 추가하여 순수한 NumPy 배열을 전달하도록 수정합니다.
        self.sma5 = self.I(lambda x: df_with_indicators['SMA_5'].values, name='SMA_5')
        self.sma20 = self.I(lambda x: df_with_indicators['SMA_20'].values, name='SMA_20')
        self.rsi = self.I(lambda x: df_with_indicators['RSI_14'].values, name='RSI_14')
        self.macd = self.I(lambda x: df_with_indicators['MACD_12_26_9'].values, name='MACD')
        self.macd_signal = self.I(lambda x: df_with_indicators['MACDs_12_26_9'].values, name='MACD_Signal')
        self.adx = self.I(lambda x: df_with_indicators['ADX_14'].values, name='ADX')
        self.dmp = self.I(lambda x: df_with_indicators['DMP_14'].values, name='+DI')
        self.dmn = self.I(lambda x: df_with_indicators['DMN_14'].values, name='-DI')
        self.volume_sma = self.I(lambda x: df_with_indicators['Volume_SMA_20'].values, name='Volume_SMA')
        # --- [수정 끝] ---

    def next(self):
        """
        데이터의 매 캔들(시간)마다 호출되는 함수.
        여기서 매매 결정을 내립니다.
        """
        current_volume = self.data.Volume[-1]

        buy_score = 0

        if crossover(self.sma5, self.sma20):
            score = SIGNAL_WEIGHTS["golden_cross_sma"]
            if self.adx[-1] < 25: score *= 0.5
            buy_score += score

        if crossover(self.macd, self.macd_signal):
            score = SIGNAL_WEIGHTS["macd_cross"]
            if self.adx[-1] < 25: score *= 0.5
            buy_score += score

        if self.adx[-1] > 25 and self.dmp[-1] > self.dmn[-1]:
            buy_score += SIGNAL_WEIGHTS["adx_strong_trend"]

        if self.rsi[-2] <= 30 and self.rsi[-1] > 30:
            buy_score += SIGNAL_WEIGHTS["rsi_bounce_drop"]

        if self.volume_sma[-1] > 0 and current_volume > self.volume_sma[-1] * VOLUME_SURGE_FACTOR:
            buy_score += SIGNAL_WEIGHTS["volume_surge"]

        if not self.position and buy_score >= self.signal_threshold:
            self.buy()

        elif self.position and crossover(self.sma20, self.sma5):
            self.position.close()


# --- 3. 백테스팅 실행 (변경 없음) ---
if __name__ == "__main__":

    TICKER_TO_TEST = 'NVDA'
    START_DATE = '2024-01-01'
    END_DATE = '2024-12-31'
    TIMEFRAME = '60T'

    data = load_data_for_backtest(TICKER_TO_TEST, START_DATE, END_DATE, TIMEFRAME)

    if not data.empty:
        bt = Backtest(data, SwingTradingStrategy, cash=100_000, commission=.002)
        stats = bt.run()
        print("\n--- Backtesting Results ---")
        print(stats)
        print("---------------------------\n")
        bt.plot()