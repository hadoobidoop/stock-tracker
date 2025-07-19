"""
전략 설정 파일 로더
새로운 조직화된 구조에서 전략 설정을 로드하는 유틸리티
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path to import from infrastructure
sys.path.append(str(Path(__file__).parent.parent))

try:
    from infrastructure.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback to standard logging if infrastructure not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class StrategyConfigLoader:
    """전략 설정 로더"""
    
    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # 현재 파일 기준으로 strategy_configs 디렉토리
            self.base_path = Path(__file__).parent
            
        self.strategies_path = self.base_path / "strategies"
        self.archived_path = self.base_path / "archived"
        self.index_file = self.base_path / "index.json"
    
    def load_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """개별 전략 설정을 로드합니다."""
        config_file = self._find_strategy_config_file(strategy_name)
        if not config_file:
            logger.error(f"전략 설정 파일을 찾을 수 없습니다: {strategy_name}")
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"전략 설정 로드 성공: {strategy_name}")
            return config
        except Exception as e:
            logger.error(f"전략 설정 로드 실패 ({strategy_name}): {e}")
            return None
    
    def load_multiple_strategies(self, strategy_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """여러 전략 설정을 로드합니다."""
        configs = {}
        for name in strategy_names:
            config = self.load_strategy_config(name)
            if config:
                configs[name] = config
        return configs
    
    def load_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """모든 전략 설정을 로드합니다."""
        configs = {}
        
        # 인덱스 파일에서 전략 목록 가져오기
        strategy_list = self._get_strategy_list_from_index()
        
        if strategy_list:
            for category_name, strategies in strategy_list.items():
                if category_name == "archived_files":
                    continue
                    
                for strategy in strategies:
                    strategy_name = strategy["name"]
                    config = self.load_strategy_config(strategy_name)
                    if config:
                        configs[strategy_name] = config
        else:
            # 인덱스 파일이 없으면 디렉토리를 직접 스캔
            configs = self._scan_and_load_all_strategies()
        
        logger.info(f"총 {len(configs)}개 전략 설정 로드됨")
        return configs
    
    def load_legacy_config_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """기존 형식의 설정 파일을 로드합니다 (archived 파일용)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            logger.info(f"레거시 설정 파일 로드 성공: {file_path}")
            return configs
        except Exception as e:
            logger.error(f"레거시 설정 파일 로드 실패: {e}")
            return {}
    
    def _find_strategy_config_file(self, strategy_name: str) -> Optional[Path]:
        """전략 이름으로 설정 파일을 찾습니다."""
        # 일반적인 파일명 패턴들
        possible_filenames = [
            f"{strategy_name}_config.json",
            f"{strategy_name}.json",
        ]
        
        # 모든 카테고리 디렉토리에서 검색
        for category_dir in self.strategies_path.iterdir():
            if category_dir.is_dir():
                for filename in possible_filenames:
                    config_file = category_dir / filename
                    if config_file.exists():
                        return config_file
        
        return None
    
    def _get_strategy_list_from_index(self) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """인덱스 파일에서 전략 목록을 가져옵니다."""
        if not self.index_file.exists():
            return None
            
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            return index_data.get("strategies", {})
        except Exception as e:
            logger.error(f"인덱스 파일 읽기 실패: {e}")
            return None
    
    def _scan_and_load_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """디렉토리를 직접 스캔해서 모든 전략을 로드합니다."""
        configs = {}
        
        for category_dir in self.strategies_path.iterdir():
            if category_dir.is_dir():
                for config_file in category_dir.glob("*_config.json"):
                    strategy_name = config_file.stem.replace("_config", "")
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        configs[strategy_name] = config
                        logger.debug(f"전략 스캔 로드: {strategy_name}")
                    except Exception as e:
                        logger.error(f"전략 스캔 로드 실패 ({strategy_name}): {e}")
        
        return configs
    
    def get_available_strategies(self) -> List[str]:
        """사용 가능한 전략 이름 목록을 반환합니다."""
        strategies = []
        
        # 인덱스 파일에서 가져오기
        strategy_list = self._get_strategy_list_from_index()
        if strategy_list:
            for category_name, strategy_configs in strategy_list.items():
                if category_name == "archived_files":
                    continue
                for strategy in strategy_configs:
                    strategies.append(strategy["name"])
        else:
            # 디렉토리 스캔
            for category_dir in self.strategies_path.iterdir():
                if category_dir.is_dir():
                    for config_file in category_dir.glob("*_config.json"):
                        strategy_name = config_file.stem.replace("_config", "")
                        strategies.append(strategy_name)
        
        return strategies


# 전역 로더 인스턴스
_global_loader = None

def get_strategy_config_loader() -> StrategyConfigLoader:
    """전역 전략 설정 로더를 반환합니다."""
    global _global_loader
    if _global_loader is None:
        _global_loader = StrategyConfigLoader()
    return _global_loader


def load_strategy_config(strategy_name: str) -> Optional[Dict[str, Any]]:
    """편의 함수: 개별 전략 설정 로드"""
    return get_strategy_config_loader().load_strategy_config(strategy_name)


def load_all_strategies() -> Dict[str, Dict[str, Any]]:
    """편의 함수: 모든 전략 설정 로드"""
    return get_strategy_config_loader().load_all_strategies()