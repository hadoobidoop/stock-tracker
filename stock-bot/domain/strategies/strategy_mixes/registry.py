"""
전략 조합(Strategy Mix) 레지스트리

사용 가능한 전략 조합들을 등록하고 관리하는 중앙 레지스트리
"""

from typing import Dict, Union

from .models import StrategyMixConfig

# Import individual mix configurations
from .aggressive_mix.configs.aggressive_mix_config import AGGRESSIVE_MIX_CONFIG
from .conservative_mix.configs.conservative_mix_config import CONSERVATIVE_MIX_CONFIG
from .balanced_mix.configs.balanced_mix_config import BALANCED_MIX_CONFIG


# 전략 조합 정의 - 개별 폴더에서 이관된 설정들을 중앙 집중화
# Note: The individual configs have their own dataclass types but compatible interfaces
STRATEGY_MIXES: Dict[str, Union[StrategyMixConfig, object]] = {
    "aggressive_mix": AGGRESSIVE_MIX_CONFIG,
    "conservative_mix": CONSERVATIVE_MIX_CONFIG,
    "balanced_mix": BALANCED_MIX_CONFIG,
} 