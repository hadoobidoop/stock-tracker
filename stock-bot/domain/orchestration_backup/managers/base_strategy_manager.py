"""
베이스 전략 매니저 - 모든 전략 매니저의 공통 기능을 제공하는 추상 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypeVar, Generic

import pandas as pd
from domain.orchestration.utils.strategy_manager_utils import StrategyManagerUtils

from domain.signals.models.enums import StrategyType
from infrastructure.db.models.enums import TrendType
from infrastructure.logging.logger_config import get_logger

# 전략 타입을 위한 TypeVar
StrategyT = TypeVar('StrategyT')
StrategyKeyT = TypeVar('StrategyKeyT', StrategyType, str)

logger = get_logger(__name__)


class BaseStrategyManager(ABC, Generic[StrategyT, StrategyKeyT]):
    """모든 전략 매니저의 공통 기능을 제공하는 추상 베이스 클래스"""
    
    def __init__(self):
        self.strategies: Dict[StrategyKeyT, StrategyT] = {}
        self.current_strategy: Optional[StrategyT] = None
        self.is_enabled = True
    
    @abstractmethod
    def _create_strategy(self, strategy_key: StrategyKeyT) -> Optional[StrategyT]:
        """전략을 생성하는 추상 메서드 - 각 매니저에서 구현 필요"""
        pass
    
    @abstractmethod
    def _get_default_strategy_key(self) -> Optional[StrategyKeyT]:
        """기본 전략 키를 반환하는 추상 메서드 - 각 매니저에서 구현 필요"""
        pass
    
    @abstractmethod
    def _get_strategy_display_name(self, strategy: StrategyT) -> str:
        """전략 표시명을 반환하는 추상 메서드 - 각 매니저에서 구현 필요"""
        pass
    
    @abstractmethod
    def _validate_strategy(self, strategy: StrategyT, strategy_key: StrategyKeyT) -> bool:
        """전략 검증을 위한 추상 메서드 - 각 매니저에서 구현 필요"""
        pass
    
    def initialize_strategies(self, strategy_keys: Optional[List[StrategyKeyT]] = None) -> int:
        """공통 전략 초기화 로직"""
        if not self.is_enabled:
            logger.info(f"{self.__class__.__name__} is disabled. Skipping initialization.")
            return 0
        
        if strategy_keys is None:
            strategy_keys = self._get_available_strategy_keys()
        
        logger.info(f"{self.__class__.__name__} 초기화 시작: {len(strategy_keys)}개 전략")
        
        success_count = 0
        for strategy_key in strategy_keys:
            try:
                strategy = self._create_strategy(strategy_key)
                if strategy and self._validate_strategy(strategy, strategy_key):
                    self.strategies[strategy_key] = strategy
                    success_count += 1
                    logger.info(f"전략 초기화 성공: {self._get_strategy_display_name(strategy)}")
                else:
                    logger.error(f"전략 초기화 실패: {strategy_key}")
            except Exception as e:
                logger.error(f"전략 초기화 예외 발생 {strategy_key}: {e}", exc_info=True)
                continue
        
        self._set_default_strategy()
        logger.info(f"{self.__class__.__name__} 초기화 완료: {success_count}/{len(strategy_keys)} 성공")
        return success_count
    
    def _set_default_strategy(self):
        """기본 전략 설정 공통 로직"""
        default_key = self._get_default_strategy_key()
        
        if default_key and default_key in self.strategies:
            self.current_strategy = self.strategies[default_key]
        elif self.strategies:
            # 기본 전략이 없으면 첫 번째 전략 선택
            self.current_strategy = next(iter(self.strategies.values()))
        
        if self.current_strategy:
            strategy_name = self._get_strategy_display_name(self.current_strategy)
            logger.info(f"기본 전략 설정: {strategy_name}")
    
    def switch_strategy(self, strategy_key: StrategyKeyT) -> bool:
        """공통 전략 교체 로직"""
        if strategy_key not in self.strategies:
            logger.warning(f"전략을 찾을 수 없음: {strategy_key}")
            return False
        
        self.current_strategy = self.strategies[strategy_key]
        strategy_name = self._get_strategy_display_name(self.current_strategy)
        logger.info(f"전략 교체 완료: {strategy_name}")
        return True
    
    def enable(self, is_enabled: bool = True):
        """전략 시스템 활성화/비활성화"""
        self.is_enabled = is_enabled
        status = "활성화" if is_enabled else "비활성화"
        logger.info(f"{self.__class__.__name__} {status}")
        
        if is_enabled and not self.strategies:
            self.initialize_strategies()
    
    def clear_current_strategy(self):
        """현재 전략 해제"""
        self.current_strategy = None
        logger.info(f"{self.__class__.__name__}의 현재 전략이 해제되었습니다.")
    
    def get_current_strategy_info(self) -> Optional[Dict[str, Any]]:
        """현재 전략 정보 반환"""
        if not self.current_strategy:
            return None
        
        return {
            "name": self._get_strategy_display_name(self.current_strategy),
            "manager_type": self.__class__.__name__
        }
    
    def list_strategies(self) -> List[StrategyKeyT]:
        """사용 가능한 전략 키 목록 반환"""
        return list(self.strategies.keys())
    
    def get_analysis_parameters(self, 
                              df_with_indicators: pd.DataFrame,
                              ticker: str,
                              market_trend: TrendType = TrendType.NEUTRAL,
                              long_term_trend: TrendType = TrendType.NEUTRAL,
                              daily_extra_indicators: Dict = None) -> Dict[str, Any]:
        """분석 파라미터를 표준화하여 반환"""
        return StrategyManagerUtils.get_analysis_parameters(
            df_with_indicators, ticker, market_trend, long_term_trend, daily_extra_indicators
        )
    
    @abstractmethod
    def _get_available_strategy_keys(self) -> List[StrategyKeyT]:
        """사용 가능한 전략 키들을 반환하는 추상 메서드"""
        pass
    
    @property
    def has_current_strategy(self) -> bool:
        """현재 활성화된 전략이 있는지 확인"""
        return self.current_strategy is not None
    
    @property
    def available_strategy_keys(self) -> List[StrategyKeyT]:
        """사용 가능한 전략 키들 반환"""
        return list(self.strategies.keys())
    
    @property
    def strategy_count(self) -> int:
        """로드된 전략 수 반환"""
        return len(self.strategies)