import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType

# 기존 호환성을 위한 import
from domain.analysis.service.signal_detection_service import SignalDetectionService
from domain.analysis.strategy.configs.static_strategies import StrategyType, STRATEGY_CONFIGS
from domain.analysis.strategy.base_strategy import StrategyResult

from domain.analysis.utils import calculate_all_indicators, calculate_fibonacci_levels
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.service.market_data_service import MarketDataService
from domain.analysis.config.signal_weights import SIGNAL_WEIGHTS, SIGNAL_THRESHOLD
from domain.analysis.config.signal_adjustment_factors import SIGNAL_ADJUSTMENT_FACTORS_BY_TREND
from domain.analysis.config.realtime_signal_settings import REALTIME_SIGNAL_DETECTION
from domain.analysis.config.prediction_signal_settings import (
    DAILY_PREDICTION_HOUR_ET, DAILY_PREDICTION_MINUTE_ET, PREDICTION_ATR_MULTIPLIER_FOR_RANGE, PREDICTION_SIGNAL_WEIGHTS, PREDICTION_THRESHOLD
)
from domain.stock.config.settings import MARKET_INDEX_TICKER

from ..models.trade import Trade, TradeType, TradeStatus
from ..models.portfolio import Portfolio
from ..models.backtest_result import BacktestResult

logger = get_logger(__name__)


class BacktestingEngine:
    """
    백테스팅 엔진 - 다중 전략 시스템 지원
    
    새로운 기능:
    1. 특정 전략으로 백테스팅
    2. 전략 조합으로 백테스팅  
    3. 전략 비교 백테스팅
    4. 자동 전략 선택 백테스팅
    5. 동적 전략 백테스팅 지원
    """

    def __init__(self,
                 stock_analysis_service: StockAnalysisService,
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.001,
                 risk_per_trade: float = 0.02,
                 use_enhanced_signals: bool = True,
                 strategy_type: StrategyType = None):
        self.stock_analysis_service = stock_analysis_service
        self.market_data_service = MarketDataService()
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.risk_per_trade = risk_per_trade
        self.use_enhanced_signals = use_enhanced_signals

        # 새로운 전략 시스템
        if use_enhanced_signals:
            self.signal_service = SignalDetectionService()
            self.strategy_type = strategy_type or StrategyType.BALANCED
            self._initialize_signal_service()
        else:
            self.signal_service = None

        self.daily_data_cache: Dict[str, Any] = {
            "last_updated": None,
            "market_trend": TrendType.NEUTRAL,
            "daily_extras": {},
            "long_term_trends": {},
            "long_term_trend_values": {}
        }

        logger.info(f"BacktestingEngine initialized with capital: ${initial_capital:,.2f}")
        if use_enhanced_signals:
            logger.info(f"Using enhanced strategy system with strategy: {self.strategy_type}")

    def _initialize_signal_service(self):
        """신호 감지 서비스 초기화"""
        if self.signal_service:
            try:
                all_strategies = list(STRATEGY_CONFIGS.keys())
                success = self.signal_service.initialize(all_strategies)
                if success:
                    self.signal_service.switch_strategy(self.strategy_type)
                    logger.info(f"신호 감지 서비스 초기화 완료 - 전략: {self.strategy_type}")
                else:
                    logger.warning("신호 감지 서비스 초기화 실패")
                    self.use_enhanced_signals = False
            except Exception as e:
                logger.error(f"신호 감지 서비스 초기화 오류: {e}")
                self.use_enhanced_signals = False

    def run_backtest(self,
                     tickers: List[str],
                     start_date: datetime,
                     end_date: datetime,
                     data_interval: str = '1h',
                     daily_market_data: Optional[Dict[datetime, Dict]] = None) -> BacktestResult:
        """기본 백테스트 실행 (현재 설정된 전략 사용)"""
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # 현재 활성 전략 정보 가져오기
        current_strategy_info = self._get_current_strategy_info()
        strategy_name = current_strategy_info['name']
        strategy_type_value = current_strategy_info['type']
        
        logger.info(f"Starting backtest for {len(tickers)} tickers from {start_date} to {end_date} using {strategy_name}")

        portfolio = Portfolio(
            initial_cash=self.initial_capital,
            current_cash=self.initial_capital,
            commission_rate=self.commission_rate
        )

        backtest_settings = {
            'tickers': tickers,
            'data_interval': data_interval,
            'commission_rate': self.commission_rate,
            'risk_per_trade': self.risk_per_trade,
            'signal_threshold': SIGNAL_THRESHOLD,
            'use_enhanced_signals': self.use_enhanced_signals,
            'strategy_type': strategy_type_value
        }

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=0.0,
            portfolio=portfolio,
            backtest_settings=backtest_settings
        )

        success = self._execute_backtest_logic(tickers, start_date, end_date, data_interval, portfolio, result, daily_market_data)
        
        if success:
            logger.info(f"Backtest completed using {strategy_name}. Final capital: ${result.final_capital:,.2f}")
        
        return result

    def run_strategy_backtest(self,
                            tickers: List[str],
                            start_date: datetime,
                            end_date: datetime,
                            strategy_type: Optional[StrategyType] = None,
                            strategy: Optional[Any] = None, # BaseStrategy 또는 DynamicCompositeStrategy
                            data_interval: str = '1h') -> Optional[BacktestResult]:
        
        if strategy is None and strategy_type is None:
            raise ValueError("Either strategy_type or strategy object must be provided.")

        original_strategy_type = self.strategy_type
        
        # SignalService와 상호작용하는 부분은 strategy_type이 있을 때만 유효
        if strategy_type:
            self.strategy_type = strategy_type
            if self.use_enhanced_signals and self.signal_service:
                self.signal_service.switch_strategy(strategy_type)
        
        # BacktestingEngine 자체의 strategy를 직접 설정 (동적 전략용)
        if strategy:
            # SignalDetectionService 내부의 StrategyManager가 이 strategy를 사용하도록 설정
            if self.use_enhanced_signals and self.signal_service:
                self.signal_service.strategy_manager.set_strategy(strategy)

        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            if result:
                if strategy:
                    result.backtest_settings['strategy_name'] = strategy.strategy_name
                    result.backtest_settings['strategy_type'] = 'dynamic'
                elif strategy_type:
                    result.backtest_settings['strategy_type'] = strategy_type.value
            return result
        finally:
            # 원래의 정적 전략으로 복구
            self.strategy_type = original_strategy_type
            if self.use_enhanced_signals and self.signal_service and original_strategy_type:
                self.signal_service.switch_strategy(original_strategy_type)
            
            # 동적 전략 사용 후, 기본 전략으로 리셋
            if strategy and self.use_enhanced_signals and self.signal_service:
                self.signal_service.strategy_manager.set_strategy(None) # 기본 전략으로 리셋
                self.signal_service.switch_strategy(original_strategy_type or StrategyType.BALANCED)

    def run_dynamic_strategy_backtest(self,
                                    tickers: List[str],
                                    start_date: datetime,
                                    end_date: datetime,
                                    dynamic_strategy_name: str,
                                    data_interval: str = '1h',
                                    daily_market_data: Optional[Dict[date, Dict]] = None) -> Optional[BacktestResult]:
        """동적 전략으로 백테스트 실행"""
        if not self.use_enhanced_signals or not self.signal_service:
            raise ValueError("동적 전략 백테스트는 신호 감지 서비스가 필요합니다.")

        success = self.signal_service.switch_to_dynamic_strategy(dynamic_strategy_name)
        if not success:
            raise ValueError(f"동적 전략 '{dynamic_strategy_name}'을 설정할 수 없습니다.")

        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval, daily_market_data)
            if result:
                result.backtest_settings['dynamic_strategy_name'] = dynamic_strategy_name
            return result
        finally:
            self.signal_service.switch_strategy(self.strategy_type) # 기본 정적 전략으로 복구

    def run_strategy_mix_backtest(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                mix_name: str,
                                data_interval: str = '1h') -> Optional[BacktestResult]:
        if not self.use_enhanced_signals or not self.signal_service:
            raise ValueError("전략 조합 백테스트는 신호 감지 서비스가 필요합니다.")
        
        success = self.signal_service.set_strategy_mix(mix_name)
        if not success:
            raise ValueError(f"전략 조합 '{mix_name}'을 설정할 수 없습니다.")
        
        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            if result:
                result.backtest_settings['strategy_mix'] = mix_name
            return result
        finally:
            self.signal_service.switch_strategy(self.strategy_type)

    def run_auto_strategy_backtest(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 data_interval: str = '1h') -> Optional[BacktestResult]:
        if not self.use_enhanced_signals or not self.signal_service:
            raise ValueError("자동 전략 선택 백테스트는 신호 감지 서비스가 필요합니다.")
        
        self.signal_service.enable_auto_strategy_selection(True)
        
        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            if result:
                result.backtest_settings['auto_strategy_selection'] = True
            return result
        finally:
            self.signal_service.enable_auto_strategy_selection(False)

    def compare_strategies(self,
                          tickers: List[str],
                          start_date: datetime,
                          end_date: datetime,
                          strategies: List[StrategyType],
                          data_interval: str = '1h') -> Dict[str, BacktestResult]:
        logger.info(f"Comparing {len(strategies)} strategies")
        results = {}
        for strategy_type in strategies:
            logger.info(f"Running backtest with {strategy_type.value} strategy")
            try:
                result = self.run_strategy_backtest(
                    tickers, start_date, end_date, strategy_type, data_interval
                )
                if result:
                    results[strategy_type.value] = result
                    logger.info(f"{strategy_type.value} strategy completed - "
                              f"Return: {result.total_return_percent:.2f}%, "
                              f"Win Rate: {result.win_rate:.1%}")
            except Exception as e:
                logger.error(f"Error running backtest with {strategy_type.value}: {e}")
                continue
        return results

    def _get_current_strategy_info(self) -> Dict[str, str]:
        """현재 활성 전략 정보를 반환합니다."""
        if not self.use_enhanced_signals or not self.signal_service:
            return {
                'name': 'Static_Strategy_Mix',
                'type': 'static_mix'
            }
        
        # 전략 조합이 활성화되어 있는지 확인
        if hasattr(self.signal_service.strategy_manager, 'current_mix_config') and \
           self.signal_service.strategy_manager.current_mix_config:
            mix_config = self.signal_service.strategy_manager.current_mix_config
            return {
                'name': f"Strategy Mix: {mix_config.name}",
                'type': mix_config.name
            }
        
        # 동적 전략이 활성화되어 있는지 확인
        if hasattr(self.signal_service.strategy_manager, 'current_dynamic_strategy') and \
           self.signal_service.strategy_manager.current_dynamic_strategy:
            dynamic_strategy = self.signal_service.strategy_manager.current_dynamic_strategy
            return {
                'name': f"Dynamic Strategy: {dynamic_strategy.strategy_name}",
                'type': dynamic_strategy.strategy_name
            }
        
        # 정적 전략
        strategy_type = self.strategy_type.value if hasattr(self, 'strategy_type') and self.strategy_type else 'balanced'
        return {
            'name': f"Static Strategy: {strategy_type}",
            'type': strategy_type
        }

    def _execute_backtest_logic(self,
                              tickers: List[str],
                              start_date: datetime,
                              end_date: datetime,
                              data_interval: str,
                              portfolio: Portfolio,
                              result: BacktestResult,
                              daily_market_data: Optional[Dict[date, Dict]] = None) -> bool:
        extended_start = start_date - timedelta(days=REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"])

        try:
            logger.info("Fetching historical data for all tickers and market index...")
            tickers_to_fetch = tickers + [MARKET_INDEX_TICKER]
            all_fetched_data = self.stock_analysis_service.stock_repository.fetch_and_cache_ohlcv(
                tickers_to_fetch,
                (end_date - extended_start).days,
                data_interval
            )

            all_data = {t: data for t, data in all_fetched_data.items() if t != MARKET_INDEX_TICKER and data is not None and not data.empty}
            market_index_data = all_fetched_data.get(MARKET_INDEX_TICKER)
            
            print(f"📊 Loaded data for {len(all_data)} tickers")
            for ticker, data in all_data.items():
                print(f"  {ticker}: {len(data)} rows, date range: {data.index[0]} to {data.index[-1]}")
                print(f"    Sample timestamps: {data.index[:3].tolist()}")

            if not all_data:
                logger.error("No data loaded for any ticker")
                return False
            if market_index_data is None or market_index_data.empty:
                logger.error(f"Market index data ({MARKET_INDEX_TICKER}) could not be loaded.")
                return False

            print(f"🚀 Starting backtest execution by timeframe")
            self._execute_backtest_by_timeframe(all_data, market_index_data, portfolio, result, start_date, end_date, daily_market_data)

            print(f"🏁 Finalizing backtest result")
            self._finalize_backtest_result(portfolio, result, all_data)

            return True

        except Exception as e:
            logger.error(f"Error during backtest execution: {e}", exc_info=True)
            return False

    def _execute_backtest_by_timeframe(self,
                                       all_data: Dict[str, pd.DataFrame],
                                       market_index_data: pd.DataFrame,
                                       portfolio: Portfolio,
                                       result: BacktestResult,
                                       start_date: datetime,
                                       end_date: datetime,
                                       daily_market_data: Optional[Dict[date, Dict]] = None) -> None:
        all_timestamps = set()
        for data in all_data.values():
            all_timestamps.update(data.index)

        timestamps = sorted([ts for ts in all_timestamps if start_date <= ts <= end_date])
        
        print(f"🕐 Total timestamps in range: {len(timestamps)}")
        print(f"📅 Date range: {start_date} to {end_date}")
        if timestamps:
            print(f"🔢 First timestamp: {timestamps[0]}")
            print(f"🔢 Last timestamp: {timestamps[-1]}")

        logger.info(f"Processing {len(timestamps)} time points...")

        for i, current_time in enumerate(timestamps):
            if i % 100 == 0:
                logger.info(f"Processing timestamp {i+1}/{len(timestamps)}: {current_time}")

            try:
                current_prices = {}
                for ticker, data in all_data.items():
                    if current_time in data.index:
                        current_prices[ticker] = data.loc[current_time, 'Close']

                portfolio.check_stop_loss_take_profit(current_prices, current_time)

                self._process_signals_and_trades(all_data, market_index_data, portfolio, current_time, current_prices, daily_market_data, start_date)

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
                                    current_prices: Dict[str, float],
                                    daily_market_data: Optional[Dict[date, Dict]],
                                    start_date: datetime) -> None:

        self._update_daily_cache(all_data, market_index_data, current_time)

        market_trend = self.daily_data_cache["market_trend"]

        for ticker, data in all_data.items():
            if ticker in portfolio.open_positions:
                continue
            if current_time not in data.index:
                continue

            try:
                # --- 수정된 부분: start_date를 사용하여 데이터 슬라이싱 ---
                current_data = data.loc[start_date:current_time].copy()
                if len(current_data) < REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]:
                    continue

                df_with_indicators = calculate_all_indicators(current_data)
                if df_with_indicators.empty:
                    continue

                # --- 중앙화된 데이터 공급 방식으로 변경 ---
                daily_extras = {}
                # 현재 활성화된 전략(정적/동적)을 가져옴
                current_strategy = self.signal_service.strategy_manager.active_strategy
                
                if hasattr(current_strategy, 'get_required_macro_indicators'):
                    required_indicators = current_strategy.get_required_macro_indicators()
                    if required_indicators:
                        current_date = current_time.date()
                        daily_extras = self.market_data_service.get_macro_data_for_date(
                            target_date=current_date,
                            required_indicators=required_indicators
                        )

                long_term_trend = self.daily_data_cache["long_term_trends"].get(ticker, TrendType.NEUTRAL)

                signal_result = self._detect_signals(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
                )

                if signal_result:
                    logger.info(f"📊 Signal detected for {ticker} at {current_time}: {signal_result['type']} (Score: {signal_result['score']:.2f})")
                    self._execute_trade(
                        signal_result, ticker, current_time, current_prices.get(ticker),
                        portfolio, market_trend, long_term_trend
                    )
            except Exception as e:
                logger.error(f"Error processing signals for {ticker} at {current_time}: {e}")
                continue

    def _detect_signals(self,
                       df_with_indicators: pd.DataFrame,
                       ticker: str,
                       market_trend: TrendType,
                       long_term_trend: TrendType,
                       daily_extras: Dict) -> Optional[Dict]:
        """
        향상된 신호 감지 시스템을 사용하여 신호를 감지합니다.
        StrategyResult의 has_signal을 신뢰하여 신호 유무를 판단합니다.
        """
        if not (self.use_enhanced_signals and self.signal_service and self.signal_service.is_initialized):
            return None

        try:
            strategy_result: StrategyResult = self.signal_service.analyze_with_current_strategy(
                df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
            )

            # StrategyResult가 신호가 없다고 판단하면, 즉시 종료
            if not strategy_result.has_signal:
                logger.debug(f"No signal for {ticker}: has_signal={strategy_result.has_signal}, buy_score={strategy_result.buy_score:.2f}, sell_score={strategy_result.sell_score:.2f}")
                return None
            else:
                logger.debug(f"Signal details for {ticker}: has_signal={strategy_result.has_signal}, buy_score={strategy_result.buy_score:.2f}, sell_score={strategy_result.sell_score:.2f}")

            # 신호가 있다면, buy/sell 중 어떤 타입인지 결정
            if strategy_result.buy_score > strategy_result.sell_score:
                signal_type = 'BUY'
                score = strategy_result.buy_score
            # sell_score가 높거나, 점수가 같지만 sell 액션이 제안된 경우 등
            else:
                signal_type = 'SELL'
                score = strategy_result.sell_score

            # 유효한 신호이므로, 거래 실행에 필요한 모든 정보를 담은 딕셔너리 반환
            return {
                'score': score,
                'type': signal_type,
                'details': strategy_result.signals_detected,
                'stop_loss_price': strategy_result.stop_loss_price,
                'strategy_name': strategy_result.strategy_name,
                'strategy_result': strategy_result  # 상세 분석을 위해 원본 결과 포함
            }

        except Exception as e:
            logger.warning(f"Enhanced signal detection failed for {ticker}: {e}")
            return None

    

    def _update_daily_cache(self,
                            all_data: Dict[str, pd.DataFrame],
                            market_index_data: pd.DataFrame,
                            current_time: datetime) -> None:
        current_date = current_time.date()

        if self.daily_data_cache["last_updated"] != current_date:
            logger.debug(f"Updating daily cache for {current_date}")

            market_data_so_far = market_index_data.loc[:current_time]
            self.daily_data_cache["market_trend"] = self.stock_analysis_service.get_market_trend(
                market_data=market_data_so_far
            )

            for ticker, data in all_data.items():
                try:
                    current_data = data.loc[:current_time].copy()

                    if len(current_data) >= REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"]:
                        self.daily_data_cache["daily_extras"][ticker] = calculate_fibonacci_levels(current_data)

                        trend_result = self.stock_analysis_service.get_long_term_trend(current_data)
                        self.daily_data_cache["long_term_trends"][ticker] = trend_result.trend
                        self.daily_data_cache["long_term_trend_values"][ticker] = trend_result.values
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
        if current_price is None:
            logger.debug(f"Skipping trade for {ticker} at {current_time}: No current price available.")
            return

        signal_type = signal_result.get('type')
        signal_score = signal_result.get('score', 0)
        stop_loss_price = signal_result.get('stop_loss_price')

        quantity = portfolio.calculate_position_size(
            current_price, self.risk_per_trade, stop_loss_price
        )

        if not portfolio.can_open_position(current_price, quantity):
            logger.debug(
                f"Cannot open position for {ticker}. "
                f"Cash: {portfolio.current_cash:.2f}, "
                f"Required: {current_price * quantity:.2f}, "
                f"Open Positions: {len(portfolio.open_positions)}"
            )
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
            sub_strategy_info = ""
            if "Chosen sub-strategy" in signal_result.get('details', [''])[0]:
                sub_strategy_info = f" (Sub: {signal_result['details'][0].split(': ')[-1]})"

            logger.info(
                f"TRADE EXECUTED: {trade.trade_type.value} {ticker} at ${current_price:.2f} "
                f"(Score: {signal_score:.2f}, Qty: {quantity}, "
                f"Strategy: {signal_result.get('strategy_name', 'N/A')}{sub_strategy_info})"
            )

    def _finalize_backtest_result(self,
                                  portfolio: Portfolio,
                                  result: BacktestResult,
                                  all_data: Dict[str, pd.DataFrame]) -> None:
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
