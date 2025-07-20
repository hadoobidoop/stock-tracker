from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

# 새로운 services 계층 import (Phase 4)
from domain.services import StrategyService, TradingService

from domain.signals.config.signals.service.signal_detection_service import SignalDetectionService
from domain.signals.config.signals.service.signal_processor import SignalProcessor

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

from infrastructure.logging import get_logger
from infrastructure.db.models.enums import TrendType, SignalType

# 새로운 전략 시스템 import
from domain.indicators.calculator import (
    calculate_all_indicators,
)
from domain.stock.service.stock_analysis_service import StockAnalysisService
from domain.signals.service.cache_manager import MarketDataCacheManager
from domain.signals.service.shared.repository_factory import (
    RepositoryFactory,
    IndicatorPersistenceService
)

logger = get_logger(__name__)

# 캐시 매니저 인스턴스
cache_manager = MarketDataCacheManager()

# Repository 및 Service 인스턴스 (팩토리 패턴 사용)
technical_indicator_repo = RepositoryFactory.get_technical_indicator_repository()
trading_signal_repo = RepositoryFactory.get_trading_signal_repository()
stock_repo = RepositoryFactory.get_stock_repository()
stock_analysis_service = StockAnalysisService(stock_repo)

# 기술적 지표 저장 서비스
indicator_persistence_service = IndicatorPersistenceService()

# Static Strategy Mix를 위한 오케스트레이터 인스턴스
orchestrator = SignalProcessor()

# 새로운 services 계층 인스턴스 (Phase 4)
def get_strategy_service() -> StrategyService | None:
    """새로운 services 계층의 전략 서비스를 가져옵니다."""
    try:
        from pathlib import Path
        definitions_path = Path("domain/strategies/definitions")
        return StrategyService(definitions_path)
    except Exception as e:
        logger.warning(f"새로운 전략 서비스를 가져올 수 없음: {e}. Static Strategy Mix 시스템 사용.")
        return None

def get_trading_service() -> TradingService | None:
    """새로운 services 계층의 거래 서비스를 가져옵니다."""
    try:
        strategy_service = get_strategy_service()
        if strategy_service:
            from domain.signals.repository.analysis_repository import MarketDataRepository
            market_data_repo = MarketDataRepository()
            return TradingService(strategy_service, market_data_repo)
    except Exception as e:
        logger.warning(f"새로운 거래 서비스를 가져올 수 없음: {e}")
        return None


class RealtimeSignalDetectionJob:
    """
    실시간 신호 감지 작업 (Phase 4 업데이트)
    
    개선 사항:
    1. 새로운 services 계층 사용
    2. YAML 전략 지원
    3. 폴백 메커니즘 적용
    4. 중복 설정 코드 제거
    """

    def __init__(self):
        self.stock_analysis_service = StockAnalysisService()
        self.signal_detection_service = SignalDetectionService()
        
        # 새로운 services 계층 사용
        self.strategy_service = get_strategy_service()
        self.trading_service = get_trading_service()
        
        # 통합된 전략 설정 사용
        self._load_strategy_config()
        
        # 실행 관련 설정
        self.is_running = False
        self.last_execution_time = None
        self.execution_count = 0
        self.max_executions_per_hour = 12
        
    def _load_strategy_config(self):
        """전략 설정 로드 (Phase 4 업데이트)"""
        try:
            if self.strategy_service:
                # 새로운 services 계층 사용
                available_strategies = self.strategy_service.get_strategy_names()
                logger.info(f"사용 가능한 YAML 전략: {available_strategies}")
                
                # 기본 전략 설정
                self.strategy_config = {
                    'mode': 'yaml',
                    'config': {
                        'name': 'conservative',
                        'type': 'YAML_STRATEGY'
                    }
                }
                logger.info(f"실시간 작업 전략 설정 로드 완료: {self.strategy_config['mode']}")
                
            else:
                # 폴백: 기존 시스템 사용
                self.strategy_config = {
                    'mode': 'legacy',
                    'config': {
                        'name': 'conservative',
                        'type': 'LEGACY_STRATEGY'
                    }
                }
                logger.info("기존 전략 시스템으로 폴백")
                
        except Exception as e:
            logger.error(f"전략 설정 로드 실패: {e}")
            # 폴백: 기본 전략 사용
            self.strategy_config = {
                'mode': 'fallback',
                'config': {
                    'name': 'conservative',
                    'type': 'FALLBACK_STRATEGY'
                }
            }
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

    async def _detect_signals_for_ticker(self, ticker: str, strategy_config: Dict) -> Optional[Dict]:
        """개별 종목에 대한 신호 감지"""
        try:
            # 새로운 services 계층 사용 시도
            if self.trading_service and strategy_config.get('type') == 'YAML_STRATEGY':
                try:
                    signal = self.trading_service.generate_signal_for_strategy(
                        strategy_config.get('name', 'conservative'), 
                        ticker
                    )
                    if signal:
                        return {
                            'ticker': ticker,
                            'has_signal': True,
                            'signal_type': signal.signal.value,
                            'strength': signal.strength,
                            'confidence': signal.confidence,
                            'reasons': signal.reasons,
                            'strategy': strategy_config.get('name'),
                            'timestamp': datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.warning(f"새로운 services 계층 신호 감지 실패 {ticker}: {e}")
            
            # 폴백: 기존 시스템 사용
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
        """현재 작업 상태 반환"""
        return {
            "is_running": self.is_running,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
            "execution_count": self.execution_count,
            "strategy_config": self.strategy_config,
            "services_available": {
                "strategy_service": self.strategy_service is not None,
                "trading_service": self.trading_service is not None
            }
        }

    def refresh_strategy_config(self):
        """전략 설정 새로고침"""
        self._load_strategy_config()
        logger.info("전략 설정이 새로고침되었습니다.")


def realtime_signal_detection_job():
    """실시간 신호 감지 작업 팩토리 함수"""
    return RealtimeSignalDetectionJob()


if __name__ == "__main__":
    from infrastructure.logging import setup_logging

    setup_logging()
    realtime_signal_detection_job()

