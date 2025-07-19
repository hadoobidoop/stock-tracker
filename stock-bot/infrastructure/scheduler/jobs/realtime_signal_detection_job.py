import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Coroutine

from domain.analysis.config.signals.service.signal_detection_service import SignalDetectionService
from domain.analysis.config.signals.service.signal_orchestrator import SignalDetectionOrchestrator

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))


from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType, SignalType
from infrastructure.db.repository.sql_technical_indicator_repository import SQLTechnicalIndicatorRepository
from infrastructure.db.repository.sql_trading_signal_repository import SQLTradingSignalRepository

# 새로운 전략 시스템 import
from domain.analysis.utils.strategy_selector import strategy_selector, get_current_strategy_config
from common.config.settings import StrategyMode

from domain.analysis.utils import (
    calculate_all_indicators,
    calculate_fibonacci_levels
)
from domain.analysis.repository.technical_indicator_repository import TechnicalIndicatorRepository
from domain.analysis.repository.trading_signal_repository import TradingSignalRepository
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.stock.repository.stock_repository import StockRepository
from infrastructure.db.repository.sql_stock_repository import SQLStockRepository
from domain.analysis.config.signals.signal_weights import  SIGNAL_THRESHOLD
from domain.analysis.config.signals.realtime_signal_settings import REALTIME_SIGNAL_DETECTION
from domain.analysis.utils.multi_timeframe import (
    apply_multi_timeframe_filter,
    validate_multi_timeframe_data,
    get_trend_direction_multi_timeframe,
)

logger = get_logger(__name__)

# 전역 캐시 변수 (다중 시간대 분석용으로 확장)
daily_data_cache = {
    "last_updated": None,
    "market_trend": TrendType.NEUTRAL,
    "daily_extras": {},  # 피보나치 등 기존 일봉 지표
    "long_term_trends": {},
    "long_term_trend_values": {},
    "daily_indicators": {},  # 새로 추가: 일봉 기술적 지표
    "multi_timeframe_analysis": {}  # 새로 추가: 다중 시간대 분석 결과
}

# Repository 및 Service 인스턴스
technical_indicator_repo: TechnicalIndicatorRepository = SQLTechnicalIndicatorRepository()
trading_signal_repo: TradingSignalRepository = SQLTradingSignalRepository()
stock_repo: StockRepository = SQLStockRepository()
stock_analysis_service = StockAnalysisService(stock_repo)

# Static Strategy Mix를 위한 오케스트레이터 인스턴스
orchestrator = SignalDetectionOrchestrator()


def get_strategy_service() -> SignalDetectionService | None:
    """main.py에서 초기화된 전략 서비스를 가져옵니다."""
    try:
        from main import get_strategy_service
        return get_strategy_service()
    except Exception as e:
        logger.warning(f"새로운 전략 서비스를 가져올 수 없음: {e}. Static Strategy Mix 시스템 사용.")
        return None


class RealtimeSignalDetectionJob:
    """
    실시간 신호 감지 작업
    
    개선 사항:
    1. 통합된 전략 선택 시스템 사용
    2. 환경변수 기반 전략 설정
    3. 폴백 메커니즘 적용
    4. 중복 설정 코드 제거
    """

    def __init__(self):
        self.stock_analysis_service = StockAnalysisService()
        self.signal_detection_service = SignalDetectionService()
        
        # 통합된 전략 설정 사용
        self._load_strategy_config()
        
        # 실행 관련 설정
        self.is_running = False
        self.last_execution_time = None
        self.execution_count = 0
        self.max_executions_per_hour = 12
        
    def _load_strategy_config(self):
        """전략 설정 로드"""
        try:
            self.strategy_config = get_current_strategy_config()
            logger.info(f"실시간 작업 전략 설정 로드 완료: {self.strategy_config['mode']}")
            
            if self.strategy_config.get('config'):
                config = self.strategy_config['config']
                logger.info(f"전략: {config.get('name', 'Unknown')}")
                logger.info(f"타입: {config.get('type', 'Unknown')}")
                
                if self.strategy_config.get('fallback_enabled') and self.strategy_config.get('fallback_config'):
                    logger.info("폴백 메커니즘 활성화됨")
                    
        except Exception as e:
            logger.error(f"전략 설정 로드 실패: {e}")
            # 폴백: 기본 전략 사용
            self.strategy_config = strategy_selector.get_default_strategy_config()
            logger.info("기본 전략 설정으로 폴백")

    def _get_active_tickers(self) -> List[str]:
        """활성 종목 목록 조회"""
        try:
            # 실제로는 데이터베이스나 설정에서 가져옴
            # 여기서는 샘플 종목들 사용
            return ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'AVGO', 'NFLX']
        except Exception as e:
            logger.error(f"활성 종목 목록 조회 실패: {e}")
            return ['AAPL', 'MSFT', 'NVDA']  # 폴백

    async def execute(self) -> dict[str, str] | None:
        """실시간 신호 감지 실행"""
        if self.is_running:
            logger.warning("실시간 신호 감지 작업이 이미 실행 중입니다.")
            return {"status": "already_running"}

        self.is_running = True
        execution_start_time = datetime.now()
        
        try:
            logger.info("=" * 60)
            logger.info("🔄 실시간 신호 감지 작업 시작")
            logger.info("=" * 60)
            
            # 전략 설정 다시 로드 (환경변수 변경 반영)
            self._load_strategy_config()
            
            # 활성 종목 목록 조회
            tickers = self._get_active_tickers()
            logger.info(f"📊 분석 대상 종목: {len(tickers)}개 - {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
            
            # 전략별 신호 감지
            strategy_config = self.strategy_config.get('config')
            if not strategy_config:
                raise RuntimeError("전략 설정이 없습니다.")
            
            strategy_type = strategy_config.get('type')
            logger.info(f"📋 사용 전략: {strategy_config.get('name', 'Unknown')} ({strategy_type})")
            
            detection_results = []
            
            # 종목별 신호 감지
            for ticker in tickers:
                try:
                    result = await self._detect_signals_for_ticker(ticker, strategy_config)
                    if result:
                        detection_results.append(result)
                        
                except Exception as e:
                    logger.error(f"종목 {ticker} 신호 감지 실패: {e}")
                    
                    # 폴백 메커니즘 활용
                    if self.strategy_config.get('fallback_enabled'):
                        try:
                            fallback_config = self.strategy_config.get('fallback_config')
                            if fallback_config:
                                logger.info(f"폴백 전략으로 재시도: {fallback_config.get('name')}")
                                result = await self._detect_signals_for_ticker(ticker, fallback_config)
                                if result:
                                    result['used_fallback'] = True
                                    detection_results.append(result)
                        except Exception as fallback_error:
                            logger.error(f"폴백 전략도 실패 {ticker}: {fallback_error}")
                    
                    continue
            
            # 실행 통계 업데이트
            self.execution_count += 1
            self.last_execution_time = execution_start_time
            execution_time = (datetime.now() - execution_start_time).total_seconds()
            
            # 결과 요약
            signal_count = len([r for r in detection_results if r.get('has_signal', False)])
            
            logger.info(f"✅ 실시간 신호 감지 완료")
            logger.info(f"📈 신호 발견: {signal_count}/{len(tickers)} 종목")
            logger.info(f"⏱️ 실행 시간: {execution_time:.2f}초")
            logger.info("=" * 60)
            
            return {
                "status": "success",
                "execution_time": execution_time,
                "total_tickers": len(tickers),
                "signals_found": signal_count,
                "strategy_used": strategy_config.get('name'),
                "strategy_type": strategy_type,
                "results": detection_results,
                "execution_count": self.execution_count
            }
            
        except Exception as e:
            logger.error(f"실시간 신호 감지 작업 실패: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": (datetime.now() - execution_start_time).total_seconds()
            }
            
        finally:
            self.is_running = False
            return None

    async def _detect_signals_for_ticker(self, ticker: str, strategy_config: Dict) -> Optional[Dict]:
        """개별 종목에 대한 신호 감지"""
        try:
            # 1. 주식 데이터 조회
            stock_data_dict = self.stock_analysis_service.get_stock_data_for_analysis(
                symbols=[ticker], 
                lookback_days=90,  # 3개월 분량
                interval="1h"
            )
            
            df = stock_data_dict.get(ticker)
            if df is None or df.empty:
                logger.warning(f"종목 {ticker} 데이터가 없습니다.")
                return None
            
            # 2. 기술적 지표 계산
            from domain.analysis.utils import calculate_all_indicators
            df_with_indicators = calculate_all_indicators(df)
            
            if df_with_indicators.empty:
                logger.warning(f"종목 {ticker} 지표 계산에 실패했습니다.")
                return None
            
            # 3. 시장 추세 분석
            market_trend = TrendType.NEUTRAL
            long_term_trend = TrendType.NEUTRAL
            
            # 4. 전략 타입에 따른 신호 감지
            strategy_type = strategy_config.get('type')
            
            if strategy_type == 'static':
                # 정적 전략 사용
                strategy_type_enum = strategy_config.get('strategy_type')
                result = self.signal_detection_service.detect_signals(
                    df_with_indicators=df_with_indicators,
                    ticker=ticker,
                    market_trend=market_trend,
                    long_term_trend=long_term_trend
                )
            elif strategy_type == 'dynamic':
                # 동적 전략 사용
                result = self.signal_detection_service.detect_signals_with_strategy(
                    df_with_indicators=df_with_indicators,
                    ticker=ticker,
                    strategy_type=None,  # Use current active strategy
                    market_trend=market_trend,
                    long_term_trend=long_term_trend
                )
            else:
                logger.warning(f"지원되지 않는 전략 타입: {strategy_type}")
                return None
            
            # 4. 결과 처리
            if result and result.has_signal:
                logger.info(f"🎯 {ticker}: 신호 감지 (점수: {result.total_score:.2f}, 신뢰도: {result.confidence:.1%})")
                
                # Determine signal type from the result
                if result.signal and result.signal.signal_type:
                    signal_type_value = result.signal.signal_type.value
                elif result.buy_score > result.sell_score:
                    signal_type_value = SignalType.BUY.value
                else:
                    signal_type_value = SignalType.SELL.value
                
                return {
                    "ticker": ticker,
                    "has_signal": True,
                    "signal_type": signal_type_value,
                    "total_score": result.total_score,
                    "confidence": result.confidence,
                    "strategy_used": strategy_config.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "ticker": ticker,
                    "has_signal": False,
                    "strategy_used": strategy_config.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"종목 {ticker} 신호 감지 중 오류: {e}")
            raise

    def get_status(self) -> Dict:
        """작업 상태 조회"""
        return {
            "is_running": self.is_running,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
            "execution_count": self.execution_count,
            "strategy_config": {
                "mode": self.strategy_config.get('mode'),
                "strategy_name": self.strategy_config.get('config', {}).get('name'),
                "strategy_type": self.strategy_config.get('config', {}).get('type'),
                "fallback_enabled": self.strategy_config.get('fallback_enabled', False)
            }
        }

    def refresh_strategy_config(self):
        """전략 설정 갱신"""
        logger.info("전략 설정을 갱신합니다.")
        self._load_strategy_config()
        strategy_selector.refresh_available_strategies()
        logger.info("전략 설정 갱신 완료")


def realtime_signal_detection_job():
    """
    [전략 시스템 통합] 설정 기반 전략 시스템을 사용하여 실시간 신호를 감지합니다.
    """
    global daily_data_cache

    current_et = stock_analysis_service.get_current_et_time()
    logger.info("JOB START: Real-time signal detection job (Configurable Strategy System)...")

    stocks_to_analyze = stock_analysis_service.get_stocks_to_analyze()
    if not stocks_to_analyze:
        logger.warning("No stocks marked for analysis. Skipping job.")
        return

    # 현재 전략 설정 조회
    strategy_config = get_current_strategy_config()
    strategy_mode = strategy_config["mode"]
    current_config = strategy_config["config"]
    fallback_config = strategy_config.get("fallback_config")
    
    logger.info(f"🎯 활성 전략 모드: {strategy_mode.value}")
    if current_config:
        logger.info(f"📋 현재 전략: {current_config.get('name', 'Unknown')}")
        logger.info(f"📝 설명: {current_config.get('description', 'No description')}")
    
    # 전략 시스템 결정
    strategy_service = None
    use_dynamic_system = False
    use_static_system = False
    use_static_mix_system = False
    
    if strategy_mode == StrategyMode.DYNAMIC:
        strategy_service = get_strategy_service()
        use_dynamic_system = strategy_service is not None and strategy_service.is_initialized
        logger.info(f"🧠 동적 전략 시스템 {'활성화' if use_dynamic_system else '비활성화'}")
        
    elif strategy_mode == StrategyMode.STATIC:
        use_static_system = True
        logger.info("📊 정적 전략 시스템 활성화")
        
    elif strategy_mode == StrategyMode.STATIC_MIX:
        use_static_mix_system = True
        logger.info("🔀 Static Strategy Mix 시스템 활성화")
    
    # 폴백 설정 확인
    if fallback_config and not (use_dynamic_system or use_static_system or use_static_mix_system):
        logger.warning(f"주 전략 시스템 비활성화, 폴백 전략 사용: {fallback_config.get('name', 'Unknown')}")
        use_static_system = True
        current_config = fallback_config

    # Step 1: 캐시 업데이트 확인
    if daily_data_cache["last_updated"] != current_et.date():
        logger.info("Step 1: Refreshing daily data cache...")

        # 1.1. 시장 추세 업데이트
        daily_data_cache["market_trend"] = stock_analysis_service.get_market_trend()

        # 1.2. 일봉 및 시간봉 데이터 조회
        try:
            fib_lookback = REALTIME_SIGNAL_DETECTION["FIB_LOOKBACK_DAYS"]
            lookback_period = REALTIME_SIGNAL_DETECTION["LOOKBACK_PERIOD_DAYS_FOR_INTRADAY"]

            all_daily_data = stock_analysis_service.get_stock_data_for_analysis(stocks_to_analyze, fib_lookback, '1d')
            all_hourly_data = stock_analysis_service.get_stock_data_for_analysis(stocks_to_analyze, lookback_period,
                                                                                 '1h')

            for symbol in stocks_to_analyze:
                df_daily = all_daily_data.get(symbol)
                df_hourly = all_hourly_data.get(symbol)

                if df_daily is not None and not df_daily.empty:
                    # 기존 피보나치 레벨 계산
                    fib_data = calculate_fibonacci_levels(df_daily)
                    daily_data_cache["daily_extras"][symbol] = fib_data

                    # 새로 추가: 일봉 기술적 지표 계산
                    from domain.analysis.utils import calculate_daily_indicators
                    daily_indicators = calculate_daily_indicators(df_daily)
                    daily_data_cache["daily_indicators"][symbol] = daily_indicators

                    # 일봉 기술적 지표도 DB에 저장
                    if daily_indicators is not None and not daily_indicators.empty:
                        excluded_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        daily_indicator_columns = [col for col in daily_indicators.columns
                                                   if col not in excluded_columns]
                        latest_daily_indicators = daily_indicators[daily_indicator_columns].iloc[-1:].copy()
                        technical_indicator_repo.save_indicators(latest_daily_indicators, symbol, '1d')

                    # 동적 전략 시스템인 경우 지표 프리컴퓨팅
                    if use_dynamic_system:
                        try:
                            strategy_service.precompute_indicators_for_ticker(symbol, df_daily)
                            logger.debug(f"Daily indicators precomputed for {symbol}")
                        except Exception as e:
                            logger.warning(f"Daily indicator precomputing failed for {symbol}: {e}")

                    logger.debug(f"Calculated and stored daily indicators for {symbol}: {len(daily_indicators)} bars")

                if df_hourly is not None and not df_hourly.empty:
                    long_term_trend, trend_values = stock_analysis_service.get_long_term_trend(df_hourly)
                    daily_data_cache["long_term_trends"][symbol] = long_term_trend
                    daily_data_cache["long_term_trend_values"][symbol] = trend_values

                    # 다중 시간대 분석 (일봉과 시간봉 데이터가 모두 있을 때)
                    if df_daily is not None and not df_daily.empty:
                        validation = validate_multi_timeframe_data(df_daily, df_hourly)
                        if validation['sufficient_for_analysis']:
                            trend_analysis = get_trend_direction_multi_timeframe(
                                daily_data_cache["daily_indicators"][symbol],
                                df_hourly
                            )
                            daily_data_cache["multi_timeframe_analysis"][symbol] = trend_analysis
                            logger.info(f"Multi-timeframe analysis for {symbol}: {trend_analysis}")
                        else:
                            logger.warning(f"Insufficient data for multi-timeframe analysis for {symbol}: {validation}")
                else:
                    logger.warning(f"No hourly data for {symbol}")

        except Exception as e:
            logger.error(f"An error occurred during bulk data fetching for cache: {e}")

        daily_data_cache["last_updated"] = current_et.date()
        logger.info("Daily data cache has been successfully refreshed.")
    else:
        logger.info("Step 1: Using cached daily data.")

    market_trend = daily_data_cache["market_trend"]

    # Step 2: 실시간 신호 감지
    logger.info(f"Step 2: Starting HOURLY signal detection for {len(stocks_to_analyze)} stocks...")

    for symbol in stocks_to_analyze:
        try:
            # 2.1. 시간봉 데이터 조회
            lookback_period = REALTIME_SIGNAL_DETECTION["LOOKBACK_PERIOD_DAYS_FOR_INTRADAY"]
            df_hourly = stock_analysis_service.get_stock_data_for_analysis([symbol], lookback_period, '1h').get(symbol)

            if df_hourly is None or df_hourly.empty:
                logger.warning(f"No hourly data available for {symbol}")
                continue

            min_data_length = REALTIME_SIGNAL_DETECTION["MIN_HOURLY_DATA_LENGTH"]
            if len(df_hourly) < min_data_length:
                logger.warning(f"Insufficient hourly data for {symbol}: {len(df_hourly)} < {min_data_length}")
                continue

            # 최소한의 기술적 지표 계산을 위해 추가 검증
            if len(df_hourly) < 60:  # SMA_60을 위한 최소 길이
                logger.warning(f"Insufficient data for SMA_60 calculation for {symbol}: {len(df_hourly)} < 60")
                # SMA_60 없이도 다른 지표들을 계산할 수 있도록 계속 진행

            # 2.2. 기술적 지표 계산
            if use_dynamic_system:
                # 동적 전략 시스템: 지표 프리컴퓨팅 사용
                df_with_indicators = strategy_service.precompute_indicators_for_ticker(symbol, df_hourly)
            else:
                # 정적 전략 또는 Static Strategy Mix 시스템: 기존 방식
                df_with_indicators = calculate_all_indicators(df_hourly)

            if df_with_indicators.empty:
                logger.warning(f"Failed to calculate indicators for {symbol}")
                continue

            # 디버깅: 계산된 지표들의 유효성 확인
            logger.debug(f"Calculated indicators for {symbol}:")
            for col in df_with_indicators.columns:
                if col not in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    valid_count = df_with_indicators[col].notna().sum()
                    total_count = len(df_with_indicators)
                    logger.debug(f"  {col}: {valid_count}/{total_count} valid values")
                    if valid_count > 0:
                        last_value = df_with_indicators[col].iloc[-1]
                        logger.debug(f"    Last value: {last_value}")
                    else:
                        logger.warning(f"    All values are null for {col}")

            # 2.3. 기술적 지표 저장 (repository 패턴 사용) - 자동화된 컬럼 선택
            excluded_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            indicator_columns = [col for col in df_with_indicators.columns
                                 if col not in excluded_columns]

            # 최신 시점만 저장 (효율성 개선)
            latest_indicators_df = df_with_indicators[indicator_columns].iloc[-1:].copy()
            technical_indicator_repo.save_indicators(latest_indicators_df, symbol, '1h')

            logger.info(f"Successfully saved/updated {len(indicator_columns)} technical indicators for {symbol}")

            # 2.4. 신호 감지
            daily_extras = daily_data_cache["daily_extras"].get(symbol, {})
            long_term_trend = daily_data_cache["long_term_trends"].get(symbol, TrendType.NEUTRAL)
            long_term_trend_values = daily_data_cache["long_term_trend_values"].get(symbol, {})

            # 다중 시간대 분석 결과 추가
            daily_indicators = daily_data_cache["daily_indicators"].get(symbol)
            multi_timeframe_analysis = daily_data_cache["multi_timeframe_analysis"].get(symbol, {})

            # daily_extras에 일봉 지표 데이터 추가
            enhanced_daily_extras = daily_extras.copy()
            if daily_indicators is not None and not daily_indicators.empty:
                enhanced_daily_extras["daily_indicators"] = daily_indicators.iloc[-1].to_dict()

            # 다중 시간대 분석 결과 추가
            if multi_timeframe_analysis:
                enhanced_daily_extras["multi_timeframe"] = multi_timeframe_analysis

            if use_dynamic_system:
                # 동적 전략 시스템 사용
                try:
                    strategy_result = strategy_service.detect_signals_with_strategy(
                        df_with_indicators, symbol, None,  # 현재 활성 전략 사용
                        market_trend, long_term_trend, enhanced_daily_extras
                    )

                    logger.info(f"[DYNAMIC] Strategy result for {symbol}: "
                                f"Strategy={strategy_result.strategy_name}, "
                                f"Score={strategy_result.total_score:.2f}, "
                                f"Signal={'YES' if strategy_result.has_signal else 'NO'}, "
                                f"Strength={strategy_result.signal_strength}")

                    # 신호가 있으면 저장
                    if strategy_result.has_signal and strategy_result.signal:
                        try:
                            trading_signal_repo.save_signal(strategy_result.signal)
                            logger.info(f"✅ Trading signal saved for {symbol} using {strategy_result.strategy_name}")
                        except Exception as e:
                            logger.error(f"Failed to save trading signal for {symbol}: {e}")

                    # 다중 시간대 필터 적용 (기존 로직 유지)
                    if multi_timeframe_analysis:
                        # 기존 신호 결과를 Dict 형태로 변환하여 필터 적용
                        legacy_signal_result = {
                            'score': strategy_result.total_score,
                            'type': 'BUY' if strategy_result.has_signal else None,
                            'details': strategy_result.signals_detected,
                            'stop_loss_price': None  # 필요시 구현
                        }

                        filtered_result = apply_multi_timeframe_filter(legacy_signal_result, multi_timeframe_analysis)

                        if filtered_result != legacy_signal_result:
                            logger.info(f"Multi-timeframe filter applied for {symbol}: "
                                        f"Score {strategy_result.total_score:.2f} -> {filtered_result.get('score', 0):.2f}")

                except Exception as e:
                    logger.error(f"Error in dynamic strategy system for {symbol}: {e}")
                    logger.info(f"Falling back to static/mix strategy system for {symbol}")
                    # 이 심볼에 대해서는 아래 정적 전략 사용

            if not use_dynamic_system:
                # Static Strategy Mix 시스템 사용 (백업)
                signal_result = orchestrator.detect_signals(
                    df_with_indicators, symbol, market_trend, long_term_trend, enhanced_daily_extras
                )

                if signal_result and signal_result.get('score', 0) >= SIGNAL_THRESHOLD:
                    logger.info(f"[STATIC_MIX] Signal detected for {symbol}: score={signal_result.get('score', 0):.2f}")

                    # 다중 시간대 필터 적용
                    if multi_timeframe_analysis:
                        signal_result = apply_multi_timeframe_filter(signal_result, multi_timeframe_analysis)

                    # 신호 저장 로직 (기존)
                    try:
                        from domain.analysis.models.trading_signal import TradingSignal, SignalType
                        from domain.analysis.models.trading_signal import SignalEvidence

                        signal_type = SignalType.BUY if signal_result.get('type') == 'BUY' else SignalType.SELL
                        evidence = SignalEvidence(
                            signal_timestamp=current_et,
                            ticker=symbol,
                            signal_type=signal_result.get('type', 'BUY'),
                            final_score=int(signal_result.get('score', 0)),
                            raw_signals=signal_result.get('details', []),
                            applied_filters=['Static Strategy Mix system'],
                            score_adjustments=[
                                f"Market trend: {market_trend.value}, Long term: {long_term_trend.value}"]
                        )

                        trading_signal = TradingSignal(
                            signal_id=None,
                            ticker=symbol,
                            signal_type=signal_type,
                            signal_score=signal_result.get('score', 0),
                            timestamp_utc=current_et,
                            current_price=df_with_indicators['Close'].iloc[-1],
                            market_trend=market_trend,
                            long_term_trend=long_term_trend,
                            details=signal_result.get('details', []),
                            stop_loss_price=signal_result.get('stop_loss_price'),
                            evidence=evidence
                        )

                        trading_signal_repo.save_signal(trading_signal)
                        logger.info(f"✅ Static Strategy Mix trading signal saved for {symbol}")

                    except Exception as e:
                        logger.error(f"Failed to save Static Strategy Mix trading signal for {symbol}: {e}")
                else:
                    logger.debug(
                        f"[STATIC_MIX] No significant signal for {symbol}: score={signal_result.get('score', 0) if signal_result else 0:.2f}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue

    # Step 3: 작업 완료 로그
    if use_dynamic_system:
        # 동적 전략 시스템 성능 모니터링
        try:
            performance = strategy_service.get_strategy_performance_summary()
            logger.info(f"Strategy performance summary: {performance}")
        except Exception as e:
            logger.warning(f"Failed to get strategy performance summary: {e}")

    logger.info("JOB END: Real-time signal detection job completed successfully.")


if __name__ == "__main__":
    from infrastructure.logging import setup_logging

    setup_logging()
    realtime_signal_detection_job()

