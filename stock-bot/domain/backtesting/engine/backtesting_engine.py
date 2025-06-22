import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType
from domain.analysis.service.signal_detection_service import DetectorFactory
from domain.analysis.utils import calculate_all_indicators, calculate_fibonacci_levels
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.analysis.config.analysis_settings import (
    SIGNAL_THRESHOLD,
    REALTIME_SIGNAL_DETECTION
)
from domain.stock.config.settings import MARKET_INDEX_TICKER

from ..models.trade import Trade, TradeType, TradeStatus
from ..models.portfolio import Portfolio
from ..models.backtest_result import BacktestResult

logger = get_logger(__name__)


class BacktestingEngine:
    """
    백테스팅 엔진 - Look-Ahead Bias가 제거된 버전
    """

    def __init__(self,
                 stock_analysis_service: StockAnalysisService,
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.001,
                 risk_per_trade: float = 0.02):
        self.stock_analysis_service = stock_analysis_service
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.risk_per_trade = risk_per_trade

        self.detector_factory = DetectorFactory()
        self.orchestrator = self.detector_factory.create_default_orchestrator()

        self.daily_data_cache = {
            "last_updated": None,
            "market_trend": TrendType.NEUTRAL,
            "daily_extras": {},
            "long_term_trends": {},
            "long_term_trend_values": {}
        }

        logger.info(f"BacktestingEngine initialized with capital: ${initial_capital:,.2f}")

    def run_backtest(self,
                     tickers: List[str],
                     start_date: datetime,
                     end_date: datetime,
                     data_interval: str = '1h') -> BacktestResult:
        # 입력된 날짜에 타임존이 없으면 UTC로 설정
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
            
        logger.info(f"Starting backtest for {len(tickers)} tickers from {start_date} to {end_date}")

        portfolio = Portfolio(
            initial_cash=self.initial_capital,
            current_cash=self.initial_capital,
            commission_rate=self.commission_rate
        )

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=0.0,
            portfolio=portfolio,
            backtest_settings={
                'tickers': tickers,
                'data_interval': data_interval,
                'commission_rate': self.commission_rate,
                'risk_per_trade': self.risk_per_trade,
                'signal_threshold': SIGNAL_THRESHOLD
            }
        )

        extended_start = start_date - timedelta(days=REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"])

        try:
            logger.info("Fetching historical data for all tickers and market index...")

            # [수정] 시장 지수 티커를 포함하여 모든 데이터를 한번에 조회
            tickers_to_fetch = tickers + [MARKET_INDEX_TICKER]

            # 참고: 여기서는 stock_analysis_service의 get_stock_data_for_analysis를 직접 호출하지 않고,
            # 실제로는 이 서비스 내의 repository.fetch_and_cache_ohlcv를 호출하는 것과 같습니다.
            # 백테스팅의 데이터 조회 로직은 엔진에 집중시키는 것이 좋습니다.
            all_fetched_data = self.stock_analysis_service.stock_repository.fetch_and_cache_ohlcv(
                tickers_to_fetch,
                (end_date - extended_start).days,
                data_interval
            )

            all_data = {t: data for t, data in all_fetched_data.items() if t != MARKET_INDEX_TICKER and data is not None and not data.empty}
            market_index_data = all_fetched_data.get(MARKET_INDEX_TICKER)

            if not all_data:
                logger.error("No data loaded for any ticker")
                return result
            if market_index_data is None or market_index_data.empty:
                logger.error(f"Market index data ({MARKET_INDEX_TICKER}) could not be loaded.")
                return result

            self._execute_backtest_by_timeframe(all_data, market_index_data, portfolio, result, start_date, end_date)

            self._finalize_backtest_result(portfolio, result, all_data)

            logger.info(f"Backtest completed. Final capital: ${result.final_capital:,.2f}")

        except Exception as e:
            logger.error(f"Error during backtest: {e}", exc_info=True)

        return result

    def _execute_backtest_by_timeframe(self,
                                       all_data: Dict[str, pd.DataFrame],
                                       market_index_data: pd.DataFrame, # [수정] 시장 지수 데이터 추가
                                       portfolio: Portfolio,
                                       result: BacktestResult,
                                       start_date: datetime,
                                       end_date: datetime) -> None:
        all_timestamps = set()
        for data in all_data.values():
            all_timestamps.update(data.index)

        timestamps = sorted([ts for ts in all_timestamps if start_date <= ts <= end_date])

        logger.info(f"Processing {len(timestamps)} time points...")

        for i, current_time in enumerate(timestamps):
            if i % 100 == 0:
                logger.info(f"Processing timestamp {i+1}/{len(timestamps)}: {current_time}")

            try:
                current_prices = {}
                for ticker, data in all_data.items():
                    if current_time in data.index:
                        current_prices[ticker] = data.loc[current_time, 'Close']

                closed_positions = portfolio.check_stop_loss_take_profit(current_prices, current_time)

                # [수정] market_index_data를 인자로 전달
                self._process_signals_and_trades(all_data, market_index_data, portfolio, current_time, current_prices)

                portfolio_value = portfolio.get_portfolio_value(current_prices)
                result.portfolio_values.append({
                    'timestamp': current_time,
                    'portfolio_value': portfolio_value,
                    'cash': portfolio.current_cash,
                    'positions_count': len(portfolio.open_positions)
                })

                portfolio.update_drawdown(current_prices)

            except Exception as e:
                logger.error(f"Error processing timestamp {current_time}: {e}")
                continue

    def _process_signals_and_trades(self,
                                    all_data: Dict[str, pd.DataFrame],
                                    market_index_data: pd.DataFrame,
                                    portfolio: Portfolio,
                                    current_time: datetime,
                                    current_prices: Dict[str, float]) -> None:

        # [수정] market_index_data를 인자로 전달하여 Look-Ahead Bias 방지
        self._update_daily_cache(all_data, market_index_data, current_time)

        market_trend = self.daily_data_cache["market_trend"]

        # [추가] 최대 보유 기간 체크 (5일)
        max_holding_period = timedelta(days=5)
        for ticker, position in list(portfolio.open_positions.items()):
            if current_time - position.entry_timestamp > max_holding_period:
                if ticker in current_prices:
                    portfolio.close_position(
                        ticker, current_time, current_prices[ticker],
                        ["최대 보유 기간 초과로 인한 청산"], 0, TradeStatus.CLOSED
                    )
                    logger.info(f"Position in {ticker} closed due to maximum holding period exceeded")

        for ticker, data in all_data.items():
            if ticker in portfolio.open_positions or current_time not in data.index:
                continue

            try:
                current_data = data.loc[:current_time].copy()
                if len(current_data) < REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]:
                    continue

                df_with_indicators = calculate_all_indicators(current_data)
                if df_with_indicators.empty:
                    continue

                daily_extras = self.daily_data_cache["daily_extras"].get(ticker, {})
                long_term_trend = self.daily_data_cache["long_term_trends"].get(ticker, TrendType.NEUTRAL)

                signal_result = self.orchestrator.detect_signals(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
                )

                if signal_result and signal_result.get('score', 0) >= SIGNAL_THRESHOLD:
                    self._execute_trade(
                        signal_result, ticker, current_time, current_prices.get(ticker),
                        portfolio, market_trend, long_term_trend
                    )
            except Exception as e:
                logger.error(f"Error processing signals for {ticker} at {current_time}: {e}")
                continue

    def _update_daily_cache(self,
                            all_data: Dict[str, pd.DataFrame],
                            market_index_data: pd.DataFrame, # [수정] 시장 지수 데이터 추가
                            current_time: datetime) -> None:
        current_date = current_time.date()

        if self.daily_data_cache["last_updated"] != current_date:
            logger.debug(f"Updating daily cache for {current_date}")

            # [수정] 미리 받아온 시장 데이터에서 현재 시점까지 잘라서 추세 분석
            market_data_so_far = market_index_data.loc[:current_time]
            self.daily_data_cache["market_trend"] = self.stock_analysis_service.get_market_trend(
                market_data=market_data_so_far
            )

            for ticker, data in all_data.items():
                try:
                    current_data = data.loc[:current_time].copy()

                    if len(current_data) >= REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"]:
                        self.daily_data_cache["daily_extras"][ticker] = calculate_fibonacci_levels(current_data)

                        long_term_trend, trend_values = self.stock_analysis_service.get_long_term_trend(current_data)
                        self.daily_data_cache["long_term_trends"][ticker] = long_term_trend
                        self.daily_data_cache["long_term_trend_values"][ticker] = trend_values
                except Exception as e:
                    logger.error(f"Error updating daily cache for {ticker}: {e}")
                    continue

            self.daily_data_cache["last_updated"] = current_date

    def _execute_trade(self,
                       signal_result: Dict,
                       ticker: str,
                       current_time: datetime,
                       current_price: float,
                       portfolio: Portfolio,
                       market_trend: TrendType,
                       long_term_trend: TrendType) -> None:
        # 이 메소드는 수정이 필요 없습니다.
        if current_price is None:
            return

        signal_type = signal_result.get('type')
        signal_score = signal_result.get('score', 0)
        stop_loss_price = signal_result.get('stop_loss_price')

        quantity = portfolio.calculate_position_size(
            current_price, self.risk_per_trade, stop_loss_price
        )

        if not portfolio.can_open_position(current_price, quantity):
            return

        take_profit_price = None
        if stop_loss_price:
            risk_amount = abs(current_price - stop_loss_price)
            if signal_type == 'BUY':
                take_profit_price = current_price + (risk_amount * 2)
            else:
                take_profit_price = current_price - (risk_amount * 2)

        trade = Trade(
            trade_id=str(uuid.uuid4()), ticker=ticker,
            trade_type=TradeType.BUY if signal_type == 'BUY' else TradeType.SELL,
            status=TradeStatus.OPEN, entry_timestamp=current_time, entry_price=current_price,
            entry_quantity=quantity, entry_signal_details=signal_result.get('details', []),
            entry_signal_score=signal_score, stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price, market_trend_at_entry=market_trend.value,
            long_term_trend_at_entry=long_term_trend.value
        )

        if portfolio.open_position(trade):
            logger.info(f"Opened {signal_type} position for {ticker} at ${current_price:.2f} (Score: {signal_score}, Qty: {quantity})")

    def _finalize_backtest_result(self,
                                  portfolio: Portfolio,
                                  result: BacktestResult,
                                  all_data: Dict[str, pd.DataFrame]) -> None:
        # 이 메소드는 수정이 필요 없습니다.
        if portfolio.open_positions:
            last_timestamp = max(data.index[-1] for data in all_data.values())
            last_prices = {ticker: data.iloc[-1]['Close'] for ticker, data in all_data.items() if ticker in portfolio.open_positions}

            for ticker in list(portfolio.open_positions.keys()):
                if ticker in last_prices:
                    portfolio.close_position(
                        ticker, last_timestamp, last_prices[ticker],
                        ["백테스트 종료로 인한 강제 청산"], 0, TradeStatus.CLOSED
                    )

        final_prices = {ticker: data.iloc[-1]['Close'] for ticker, data in all_data.items()}
        result.final_capital = portfolio.get_portfolio_value(final_prices)
        result.all_trades = portfolio.closed_trades.copy()
        result.calculate_metrics()

        logger.info(f"Backtest finalized - Total trades: {len(result.all_trades)}, Win rate: {result.win_rate:.1%}, Total return: {result.total_return_percent:.2f}%")

    def get_detailed_trade_log(self, result: BacktestResult) -> pd.DataFrame:
        if not result.all_trades:
            return pd.DataFrame()
        return pd.DataFrame([trade.to_dict() for trade in result.all_trades])