"""
Strategy Service - YAML 전략 해석기

YAML 파일을 읽고 파이썬 객체로 변환하는 책임을 가진 서비스
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


@dataclass
class StrategyDefinition:
    """YAML에서 로드된 전략 정의"""
    strategy_name: str
    strategy_info: Dict[str, Any]
    signal_config: Dict[str, Any]
    position_management: Dict[str, Any]
    risk_management: Dict[str, Any]
    detectors: Dict[str, Any]
    trading_rules: Dict[str, Any]
    market_filters: Optional[Dict[str, Any]] = None
    
    @property
    def buy_rules(self) -> List[Dict[str, Any]]:
        """매수 규칙 반환"""
        return self.trading_rules.get('buy_conditions', [])
    
    @property
    def sell_rules(self) -> List[Dict[str, Any]]:
        """매도 규칙 반환"""
        return self.trading_rules.get('sell_conditions', [])
    
    @property
    def portfolio(self) -> Dict[str, Any]:
        """포트폴리오 설정 반환"""
        return {
            'order_size': self.position_management.get('max_positions', 1),
            'position_timeout': self.position_management.get('position_hold_hours', 24),
            **self.risk_management
        }


class StrategyService:
    """YAML 전략 정의 로드 및 관리 서비스"""
    
    def __init__(self, definitions_path: Path):
        self.path = definitions_path
        self.strategies: Dict[str, StrategyDefinition] = {}
        self._load_all()
    
    def _load_all(self):
        """모든 YAML 전략 파일을 로드"""
        if not self.path.exists():
            raise FileNotFoundError(f"Strategy definitions path not found: {self.path}")
        
        for file_path in self.path.glob("*.yml"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                # YAML 구조 검증
                self._validate_strategy_data(data, file_path.name)
                
                # StrategyDefinition 객체 생성
                strategy_def = StrategyDefinition(
                    strategy_name=data['strategy_info']['name'],
                    strategy_info=data['strategy_info'],
                    signal_config=data['signal_config'],
                    position_management=data['position_management'],
                    risk_management=data['risk_management'],
                    detectors=data['detectors'],
                    trading_rules=data['trading_rules'],
                    market_filters=data.get('market_filters')
                )
                
                self.strategies[file_path.stem] = strategy_def
                
            except Exception as e:
                print(f"Warning: Failed to load strategy from {file_path.name}: {e}")
    
    def _validate_strategy_data(self, data: Dict[str, Any], filename: str):
        """YAML 데이터 구조 검증"""
        required_fields = [
            'strategy_info', 'signal_config', 'position_management',
            'risk_management', 'detectors', 'trading_rules'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in {filename}")
        
        # strategy_info 내부 필수 필드 검증
        if 'name' not in data.get('strategy_info', {}):
            raise ValueError(f"Missing required field 'strategy_info.name' in {filename}")
    
    def get_strategy(self, name: str) -> Optional[StrategyDefinition]:
        """전략 이름으로 전략 정의 조회"""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> Dict[str, StrategyDefinition]:
        """모든 전략 정의 반환"""
        return self.strategies.copy()
    
    def get_strategy_names(self) -> List[str]:
        """사용 가능한 전략 이름 목록 반환"""
        return list(self.strategies.keys())
    
    def reload_strategy(self, name: str) -> bool:
        """특정 전략 재로드"""
        strategy_file = self.path / f"{name}.yml"
        if not strategy_file.exists():
            return False
        
        try:
            with open(strategy_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self._validate_strategy_data(data, strategy_file.name)
            
            strategy_def = StrategyDefinition(
                strategy_name=data['strategy_info']['name'],
                strategy_info=data['strategy_info'],
                signal_config=data['signal_config'],
                position_management=data['position_management'],
                risk_management=data['risk_management'],
                detectors=data['detectors'],
                trading_rules=data['trading_rules'],
                market_filters=data.get('market_filters')
            )
            
            self.strategies[name] = strategy_def
            return True
            
        except Exception as e:
            print(f"Failed to reload strategy {name}: {e}")
            return False
    
    def reload_all(self):
        """모든 전략 재로드"""
        self.strategies.clear()
        self._load_all()