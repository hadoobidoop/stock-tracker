import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType

# 기존 호환성을 위한 import
from domain.analysis.service.signal_detection_service import DetectorFactory

# 새로운 전략 시스템 import
from domain.analysis.service.signal_detection_service import EnhancedSignalDetectionService
from domain.analysis.config.strategy_settings import StrategyType, STRATEGY_CONFIGS
from domain.analysis.strategy.base_strategy import StrategyResult

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
    백테스팅 엔진 - 다중 전략 시스템 지원
    
    새로운 기능:
    1. 특정 전략으로 백테스팅
    2. 전략 조합으로 백테스팅  
    3. 전략 비교 백테스팅
    4. 자동 전략 선택 백테스팅
    5. 기존 레거시 방식 지원
    """

    def __init__(self,
                 stock_analysis_service: StockAnalysisService,
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.001,
                 risk_per_trade: float = 0.02,
                 use_enhanced_signals: bool = True,
                 strategy_type: StrategyType = None):
        self.stock_analysis_service = stock_analysis_service
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.risk_per_trade = risk_per_trade
        self.use_enhanced_signals = use_enhanced_signals

        # 새로운 전략 시스템
        if use_enhanced_signals:
            self.enhanced_service = EnhancedSignalDetectionService()
            self.strategy_type = strategy_type or StrategyType.BALANCED
            self._initialize_enhanced_service()
        else:
            self.enhanced_service = None

        # 기존 호환성을 위한 레거시 시스템
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
        if use_enhanced_signals:
            logger.info(f"Using enhanced strategy system with strategy: {self.strategy_type}")
        else:
            logger.info("Using legacy detector system")

    def _initialize_enhanced_service(self):
        """향상된 신호 감지 서비스 초기화"""
        if self.enhanced_service:
            try:
                # STRATEGY_CONFIGS에 정의된 모든 전략을 초기화
                all_strategies = list(STRATEGY_CONFIGS.keys())
                
                success = self.enhanced_service.initialize(all_strategies)
                if success:
                    self.enhanced_service.switch_strategy(self.strategy_type)
                    logger.info(f"Enhanced signal detection service initialized with all strategies, current: {self.strategy_type}")
                else:
                    logger.warning("Failed to initialize enhanced service, falling back to legacy")
                    self.use_enhanced_signals = False
            except Exception as e:
                logger.error(f"Error initializing enhanced service: {e}")
                self.use_enhanced_signals = False

    def run_backtest(self,
                     tickers: List[str],
                     start_date: datetime,
                     end_date: datetime,
                     data_interval: str = '1h') -> BacktestResult:
        """기본 백테스트 실행 (현재 설정된 전략 사용)"""
        # 입력된 날짜에 타임존이 없으면 UTC로 설정
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
            
        strategy_name = self.strategy_type.value if self.use_enhanced_signals else "Legacy"
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
            'strategy_type': self.strategy_type.value if self.strategy_type else None
        }

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=0.0,
            portfolio=portfolio,
            backtest_settings=backtest_settings
        )

        # 백테스트 실행
        success = self._execute_backtest_logic(tickers, start_date, end_date, data_interval, portfolio, result)
        
        if success:
            logger.info(f"Backtest completed using {strategy_name}. Final capital: ${result.final_capital:,.2f}")
        
        return result

    def run_strategy_backtest(self,
                            tickers: List[str],
                            start_date: datetime,
                            end_date: datetime,
                            strategy_type: StrategyType,
                            data_interval: str = '1h') -> BacktestResult:
        """특정 전략으로 백테스트 실행"""
        # 전략 변경
        original_strategy = self.strategy_type
        self.strategy_type = strategy_type
        
        if self.use_enhanced_signals and self.enhanced_service:
            self.enhanced_service.switch_strategy(strategy_type)
        
        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            result.backtest_settings['strategy_type'] = strategy_type.value
            return result
        finally:
            # 원래 전략으로 복구
            self.strategy_type = original_strategy
            if self.use_enhanced_signals and self.enhanced_service:
                self.enhanced_service.switch_strategy(original_strategy)

    def run_strategy_mix_backtest(self,
                                tickers: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                mix_name: str,
                                data_interval: str = '1h') -> BacktestResult:
        """전략 조합으로 백테스트 실행"""
        if not self.use_enhanced_signals or not self.enhanced_service:
            raise ValueError("전략 조합 백테스트는 향상된 신호 감지 서비스가 필요합니다.")
        
        # 전략 조합 설정
        success = self.enhanced_service.set_strategy_mix(mix_name)
        if not success:
            raise ValueError(f"전략 조합 '{mix_name}'을 설정할 수 없습니다.")
        
        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            result.backtest_settings['strategy_mix'] = mix_name
            return result
        finally:
            # 단일 전략으로 복구
            self.enhanced_service.switch_strategy(self.strategy_type)

    def run_auto_strategy_backtest(self,
                                 tickers: List[str],
                                 start_date: datetime,
                                 end_date: datetime,
                                 data_interval: str = '1h') -> BacktestResult:
        """자동 전략 선택으로 백테스트 실행"""
        if not self.use_enhanced_signals or not self.enhanced_service:
            raise ValueError("자동 전략 선택 백테스트는 향상된 신호 감지 서비스가 필요합니다.")
        
        # 자동 전략 선택 활성화
        self.enhanced_service.enable_auto_strategy_selection(True)
        
        try:
            result = self.run_backtest(tickers, start_date, end_date, data_interval)
            result.backtest_settings['auto_strategy_selection'] = True
            return result
        finally:
            # 자동 선택 비활성화
            self.enhanced_service.enable_auto_strategy_selection(False)

    def compare_strategies(self,
                          tickers: List[str],
                          start_date: datetime,
                          end_date: datetime,
                          strategies: List[StrategyType],
                          data_interval: str = '1h') -> Dict[str, BacktestResult]:
        """여러 전략으로 동시에 백테스트하여 비교"""
        logger.info(f"Comparing {len(strategies)} strategies")
        
        results = {}
        
        for strategy_type in strategies:
            logger.info(f"Running backtest with {strategy_type.value} strategy")
            
            try:
                result = self.run_strategy_backtest(
                    tickers, start_date, end_date, strategy_type, data_interval
                )
                results[strategy_type.value] = result
                
                logger.info(f"{strategy_type.value} strategy completed - "
                          f"Return: {result.total_return_percent:.2f}%, "
                          f"Win Rate: {result.win_rate:.1%}")
                
            except Exception as e:
                logger.error(f"Error running backtest with {strategy_type.value}: {e}")
                continue
        
        return results

    def _execute_backtest_logic(self,
                              tickers: List[str],
                              start_date: datetime,
                              end_date: datetime,
                              data_interval: str,
                              portfolio: Portfolio,
                              result: BacktestResult) -> bool:
        """백테스트 로직 실행"""
        extended_start = start_date - timedelta(days=REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"])

        try:
            logger.info("Fetching historical data for all tickers and market index...")

            # 시장 지수 티커를 포함하여 모든 데이터를 한번에 조회
            tickers_to_fetch = tickers + [MARKET_INDEX_TICKER]

            all_fetched_data = self.stock_analysis_service.stock_repository.fetch_and_cache_ohlcv(
                tickers_to_fetch,
                (end_date - extended_start).days,
                data_interval
            )

            all_data = {t: data for t, data in all_fetched_data.items() if t != MARKET_INDEX_TICKER and data is not None and not data.empty}
            market_index_data = all_fetched_data.get(MARKET_INDEX_TICKER)

            if not all_data:
                logger.error("No data loaded for any ticker")
                return False
            if market_index_data is None or market_index_data.empty:
                logger.error(f"Market index data ({MARKET_INDEX_TICKER}) could not be loaded.")
                return False

            self._execute_backtest_by_timeframe(all_data, market_index_data, portfolio, result, start_date, end_date)

            self._finalize_backtest_result(portfolio, result, all_data)

            return True

        except Exception as e:
            logger.error(f"Error during backtest execution: {e}", exc_info=True)
            return False

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

        # market_index_data를 인자로 전달하여 Look-Ahead Bias 방지
        self._update_daily_cache(all_data, market_index_data, current_time)

        market_trend = self.daily_data_cache["market_trend"]

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

                # 신호 감지 - 새로운 전략 시스템 또는 레거시 시스템 사용
                signal_result = self._detect_signals(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
                )

                if signal_result and self._is_valid_signal(signal_result):
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
        """신호 감지 - 새로운 전략 시스템 또는 레거시 시스템 사용"""
        
        if self.use_enhanced_signals and self.enhanced_service and self.enhanced_service.is_initialized:
            try:
                # 새로운 전략 시스템 사용
                strategy_result: StrategyResult = self.enhanced_service.analyze_with_current_strategy(
                    df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
                )
                
                # StrategyResult를 레거시 형태로 변환
                return {
                    'score': strategy_result.total_score,
                    'type': 'BUY' if strategy_result.has_signal else None,
                    'details': strategy_result.signals_detected,
                    'stop_loss_price': None,  # 필요시 구현
                    'strategy_name': strategy_result.strategy_name,
                    'strategy_result': strategy_result  # 추가 정보 보존
                }
                
            except Exception as e:
                logger.warning(f"Enhanced signal detection failed for {ticker}: {e}, falling back to legacy")
                # 폴백: 레거시 시스템 사용
        
        # 레거시 시스템 사용
        return self.orchestrator.detect_signals(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extras
        )

    def _is_valid_signal(self, signal_result: Dict) -> bool:
        """신호 유효성 검사"""
        if not signal_result:
            return False
        
        score = signal_result.get('score', 0)
        signal_type = signal_result.get('type')
        
        # 새로운 전략 시스템의 경우
        if 'strategy_result' in signal_result:
            strategy_result: StrategyResult = signal_result['strategy_result']
            return strategy_result.has_signal
        
        # 레거시 시스템의 경우
        return score >= SIGNAL_THRESHOLD and signal_type is not None

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