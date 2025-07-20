"""
YAML 전략 팩토리 (YAML Strategy Factory)

YAML 기반 전략 시스템과 기존 전략 시스템을 통합하는 팩토리 클래스입니다.
점진적으로 기존 전략들을 YAML 전략으로 전환할 수 있도록 지원합니다.
"""

from typing import Dict, Optional, Union
from pathlib import Path

from domain.signals.models.enums import StrategyType
from domain.strategies.interpreter import YAMLStrategyInterpreter, YAMLBasedStrategy
from domain.strategies.portfolio import PortfolioManager, PortfolioConfig

# 기존 전략 import (하위 호환성)
from domain.strategies.single.conservative.conservative_strategy import ConservativeStrategy
from domain.strategies.single.balanced.balanced_strategy import BalancedStrategy
from domain.strategies.single.aggressive.aggressive_strategy import AggressiveStrategy
from domain.strategies.single.momentum.momentum_strategy import MomentumStrategy
from domain.strategies.single.mean_reversion.mean_reversion_strategy import MeanReversionStrategy

# 기존 설정 import
from domain.strategies.single.conservative.configs.conservative_config import ConservativeStrategyConfig
from domain.strategies.single.balanced.configs.balanced_config import BalancedStrategyConfig
from domain.strategies.single.aggressive.configs.aggressive_config import AggressiveStrategyConfig
from domain.strategies.single.momentum.configs.momentum_config import MomentumStrategyConfig
from domain.strategies.single.mean_reversion.configs.mean_reversion_config import MeanReversionStrategyConfig


class YAMLStrategyFactory:
    """YAML 전략 팩토리"""
    
    # YAML 전략으로 전환 완료된 전략들
    YAML_STRATEGIES = {
        'conservative',
        'balanced', 
        'aggressive',
        'momentum',
        'mean_reversion',
        'scalping',
        'swing',
        'trend_following',
        'trend_pullback',
        'volatility_breakout',
        'multi_timeframe'
    }
    
    # 기존 Python 클래스 매핑 (하위 호환성)
    LEGACY_STRATEGY_MAP = {
        StrategyType.CONSERVATIVE: (ConservativeStrategy, ConservativeStrategyConfig),
        StrategyType.BALANCED: (BalancedStrategy, BalancedStrategyConfig),
        StrategyType.AGGRESSIVE: (AggressiveStrategy, AggressiveStrategyConfig),
        StrategyType.MOMENTUM: (MomentumStrategy, MomentumStrategyConfig),
        StrategyType.MEAN_REVERSION: (MeanReversionStrategy, MeanReversionStrategyConfig),
    }
    
    def __init__(self, strategies_path: str = "domain/strategies/definitions"):
        self.interpreter = YAMLStrategyInterpreter(strategies_path)
        self.strategies_path = Path(strategies_path)
        
    def create_strategy(self, strategy_name: str, strategy_type: Optional[StrategyType] = None,
                        use_yaml: bool = True) -> Union[YAMLBasedStrategy, object]:
        """
        전략을 생성합니다. YAML 우선, 실패시 기존 Python 클래스 사용
        
        Args:
            strategy_name: 전략명 (예: 'conservative', 'balanced')
            strategy_type: 전략 타입 (기존 시스템 호환용)
            use_yaml: YAML 전략 사용 여부
            
        Returns:
            전략 인스턴스 (YAML 기반 또는 기존 Python 클래스)
        """
        
        # 1. YAML 전략 우선 시도
        if use_yaml and strategy_name.lower() in self.YAML_STRATEGIES:
            try:
                yaml_file = self.strategies_path / f"{strategy_name.lower()}.yml"
                if yaml_file.exists():
                    return self.interpreter.create_strategy(strategy_name.lower())
            except Exception as e:
                print(f"YAML 전략 생성 실패 ({strategy_name}): {e}")
                print("기존 Python 전략으로 폴백합니다.")
        
        # 2. 기존 Python 클래스 폴백
        if strategy_type and strategy_type in self.LEGACY_STRATEGY_MAP:
            strategy_class, config_class = self.LEGACY_STRATEGY_MAP[strategy_type]
            config = config_class()
            return strategy_class(strategy_type, config)
            
        # 3. 전략명으로 타입 추론하여 재시도
        if strategy_name and not strategy_type:
            inferred_type = self._infer_strategy_type(strategy_name)
            if inferred_type and inferred_type in self.LEGACY_STRATEGY_MAP:
                strategy_class, config_class = self.LEGACY_STRATEGY_MAP[inferred_type]
                config = config_class()
                return strategy_class(inferred_type, config)
        
        raise ValueError(f"전략을 생성할 수 없습니다: {strategy_name} (type: {strategy_type})")
        
    def _infer_strategy_type(self, strategy_name: str) -> Optional[StrategyType]:
        """전략명으로부터 전략 타입을 추론합니다."""
        name_lower = strategy_name.lower()
        
        if 'conservative' in name_lower:
            return StrategyType.CONSERVATIVE
        elif 'balanced' in name_lower:
            return StrategyType.BALANCED
        elif 'aggressive' in name_lower:
            return StrategyType.AGGRESSIVE
        elif 'momentum' in name_lower:
            return StrategyType.MOMENTUM
        elif 'mean_reversion' in name_lower or 'reversion' in name_lower:
            return StrategyType.MEAN_REVERSION
        elif 'trend' in name_lower:
            return StrategyType.TREND_FOLLOWING
        elif 'scalp' in name_lower:
            return StrategyType.SCALPING
        elif 'swing' in name_lower:
            return StrategyType.SWING
        elif 'volatility' in name_lower:
            return StrategyType.VOLATILITY_BREAKOUT
        
        return None
        
    def create_portfolio_manager(self, strategy_name: str, total_balance: float) -> PortfolioManager:
        """
        전략에 맞는 포트폴리오 매니저를 생성합니다.
        
        Args:
            strategy_name: 전략명
            total_balance: 총 잔액
            
        Returns:
            PortfolioManager: 포트폴리오 매니저 인스턴스
        """
        return PortfolioManager(total_balance)
        
    def get_strategy_config(self, strategy_name: str) -> Optional[PortfolioConfig]:
        """
        전략의 포트폴리오 설정을 반환합니다.
        
        Args:
            strategy_name: 전략명
            
        Returns:
            Optional[PortfolioConfig]: 포트폴리오 설정
        """
        try:
            # YAML 전략에서 설정 로드
            if strategy_name.lower() in self.YAML_STRATEGIES:
                yaml_config = self.interpreter.load_strategy(strategy_name.lower())
                config_dict = {
                    'position_management': yaml_config.position_management,
                    'risk_management': yaml_config.risk_management,
                    'market_filters': yaml_config.market_filters
                }
                return PortfolioConfig.from_yaml_config(config_dict)
        except Exception as e:
            print(f"YAML 설정 로드 실패 ({strategy_name}): {e}")
            
        # 기존 설정으로 폴백
        return self._get_legacy_portfolio_config(strategy_name)
        
    def _get_legacy_portfolio_config(self, strategy_name: str) -> PortfolioConfig:
        """기존 전략의 포트폴리오 설정을 생성합니다."""
        strategy_type = self._infer_strategy_type(strategy_name)
        
        # 기본값들
        defaults = {
            'max_positions': 5,
            'position_hold_hours': 168,
            'risk_per_trade': 0.02,
            'stop_loss_percentage': 5.0,
            'take_profit_percentage': 10.0,
            'market_filters': {}
        }
        
        # 전략별 특화 설정
        if strategy_type == StrategyType.CONSERVATIVE:
            defaults.update({
                'max_positions': 3,
                'position_hold_hours': 672,
                'risk_per_trade': 0.01,
                'take_profit_percentage': 12.0
            })
        elif strategy_type == StrategyType.AGGRESSIVE:
            defaults.update({
                'max_positions': 8,
                'position_hold_hours': 168,
                'risk_per_trade': 0.03,
                'take_profit_percentage': 8.0
            })
        elif strategy_type == StrategyType.MOMENTUM:
            defaults.update({
                'max_positions': 4,
                'position_hold_hours': 24,
                'risk_per_trade': 0.025
            })
            
        return PortfolioConfig(
            max_positions=defaults['max_positions'],
            position_hold_hours=defaults['position_hold_hours'],
            risk_per_trade=defaults['risk_per_trade'],
            stop_loss_percentage=defaults['stop_loss_percentage'],
            take_profit_percentage=defaults['take_profit_percentage'],
            market_filters=defaults['market_filters']
        )
        
    def list_available_strategies(self) -> Dict[str, list]:
        """
        사용 가능한 전략 목록을 반환합니다.
        
        Returns:
            Dict: YAML 전략과 기존 전략 목록
        """
        yaml_strategies = []
        for strategy_name in self.YAML_STRATEGIES:
            yaml_file = self.strategies_path / f"{strategy_name}.yml"
            if yaml_file.exists():
                yaml_strategies.append(strategy_name)
                
        legacy_strategies = [strategy_type.value for strategy_type in self.LEGACY_STRATEGY_MAP.keys()]
        
        return {
            'yaml_strategies': yaml_strategies,
            'legacy_strategies': legacy_strategies,
            'all_strategies': yaml_strategies + legacy_strategies
        }
        
    def is_yaml_strategy(self, strategy_name: str) -> bool:
        """
        전략이 YAML 기반인지 확인합니다.
        
        Args:
            strategy_name: 전략명
            
        Returns:
            bool: YAML 전략 여부
        """
        return strategy_name.lower() in self.YAML_STRATEGIES
        
    def migrate_strategy_to_yaml(self, strategy_type: StrategyType, output_path: Optional[str] = None):
        """
        기존 Python 전략을 YAML로 마이그레이션합니다.
        
        Args:
            strategy_type: 전략 타입
            output_path: 출력 경로 (기본: strategies/definitions/)
        """
        if strategy_type not in self.LEGACY_STRATEGY_MAP:
            raise ValueError(f"지원하지 않는 전략 타입: {strategy_type}")
            
        strategy_class, config_class = self.LEGACY_STRATEGY_MAP[strategy_type]
        config = config_class()
        
        # YAML 구조 생성
        yaml_content = self._convert_config_to_yaml(config, strategy_type)
        
        # 파일 저장
        if output_path is None:
            output_path = self.strategies_path / f"{strategy_type.value.lower()}.yml"
        else:
            output_path = Path(output_path)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
            
        print(f"전략 마이그레이션 완료: {output_path}")
        
    def _convert_config_to_yaml(self, config, strategy_type: StrategyType) -> str:
        """설정 객체를 YAML 문자열로 변환합니다."""
        # 이는 실제 구현에서는 각 config 객체의 속성을 읽어서
        # YAML 형식으로 변환하는 로직이 필요합니다.
        # 현재는 기본 템플릿을 반환합니다.
        
        template = f"""# {strategy_type.value} 전략
# 자동 생성된 YAML 설정 파일

strategy_info:
  name: "{strategy_type.value} 전략"
  description: "자동 마이그레이션된 전략"
  version: "1.0.0"
  author: "Stock-Bot Team"
  created_date: "2025-01-20"

signal_config:
  threshold: {getattr(config, 'signal_threshold', 8.0)}
  score_multiplier: {getattr(config, 'score_multiplier', 1.0)}

# ... 나머지 설정들 ...
"""
        return template


# 글로벌 인스턴스
yaml_strategy_factory = YAMLStrategyFactory()