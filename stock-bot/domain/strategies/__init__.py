"""
전략별 패키지 구조
각 전략은 독립적인 패키지로 구성되어 configs/, detectors/ 등을 포함
"""

```python:domain/strategies/balanced/__init__.py
"""
균형 전략 패키지
- balanced_strategy.py: 전략 구현체
- configs/: 전략별 설정
- detectors/: 전략별 커스텀 Detector
"""

```python:domain/strategies/balanced/configs/__init__.py
"""
균형 전략 설정 패키지
"""

```python:domain/strategies/balanced/detectors/__init__.py
"""
균형 전략 커스텀 Detector 패키지
"""

## 2단계: Aggressive 전략 구현

```python:domain/strategies/aggressive/__init__.py
"""
공격적 전략 패키지
- aggressive_strategy.py: 전략 구현체
- configs/: 전략별 설정
- detectors/: 전략별 커스텀 Detector
"""

```python:domain/strategies/aggressive/configs/__init__.py
"""
공격적 전략 설정 패키지
"""

```python:domain/strategies/aggressive/configs/aggressive_config.py
from dataclasses import dataclass
from typing import Dict, Any
from domain.analysis.strategy.configs.static_strategies import StrategyConfig, StrategyType


@dataclass
class AggressiveStrategyConfig(StrategyConfig):
    """공격적 전략 설정"""
    
    # 기본 전략 설정 상속
    strategy_type: StrategyType = StrategyType.AGGRESSIVE
    signal_threshold: float = 5.0  # 낮은 임계값 (기본 8.0 → 5.0)
    max_positions: int = 8  # 더 많은 포지션 (기본 4 → 8)
    position_hold_hours: int = 48  # 더 짧은 보유 기간 (기본 72 → 48)
    stop_loss_percentage: float = 5.0  # 기본값 유지
    take_profit_percentage: float = 12.0  # 기본값 유지
    
    # Aggressive 전략 특화 설정
    score_multiplier: float = 1.2  # 점수 조정 (기본 × 1.2)
    long_term_bullish_multiplier: float = 1.3  # 장기 상승장 배수 (기본 1.2 → 1.3)
    long_term_bearish_multiplier: float = 1.2  # 장기 하락장 배수
    
    # Detector 가중치 (높은 가중치)
    detector_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.detector_weights is None:
            self.detector_weights = {
                'sma': 4.0,
                'macd': 4.0,
                'rsi': 3.0,
                'stoch': 3.0,
                'volume': 3.0,
                'adx': 3.0
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            'strategy_type': self.strategy_type.value,
            'signal_threshold': self.signal_threshold,
            'max_positions': self.max_positions,
            'position_hold_hours': self.position_hold_hours,
            'stop_loss_percentage': self.stop_loss_percentage,
            'take_profit_percentage': self.take_profit_percentage,
            'score_multiplier': self.score_multiplier,
            'long_term_bullish_multiplier': self.long_term_bullish_multiplier,
            'long_term_bearish_multiplier': self.long_term_bearish_multiplier,
            'detector_weights': self.detector_weights
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AggressiveStrategyConfig':
        """딕셔너리에서 설정 생성"""
        return cls(
            strategy_type=StrategyType(data['strategy_type']),
            signal_threshold=data.get('signal_threshold', 5.0),
            max_positions=data.get('max_positions', 8),
            position_hold_hours=data.get('position_hold_hours', 48),
            stop_loss_percentage=data.get('stop_loss_percentage', 5.0),
            take_profit_percentage=data.get('take_profit_percentage', 12.0),
            score_multiplier=data.get('score_multiplier', 1.2),
            long_term_bullish_multiplier=data.get('long_term_bullish_multiplier', 1.3),
            long_term_bearish_multiplier=data.get('long_term_bearish_multiplier', 1.2),
            detector_weights=data.get('detector_weights', {
                'sma': 4.0, 'macd': 4.0, 'rsi': 3.0, 
                'stoch': 3.0, 'volume': 3.0, 'adx': 3.0
            })
        )
```

```python:domain/strategies/aggressive/detectors/__init__.py
"""
공격적 전략 커스텀 Detector 패키지
"""

```python:domain/strategies/aggressive/detectors/aggressive_volume_detector.py
from typing import Dict, List, Tuple
import pandas as pd
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger
from domain.analysis.detectors.volume.volume_detector import VolumeSignalDetector
from domain.analysis.models.trading_signal import TechnicalIndicatorEvidence

logger = get_logger(__name__)


class AggressiveVolumeDetector(VolumeSignalDetector):
    """공격적 전략용 거래량 신호 감지기 - 민감한 신호 감지"""
    
    def __init__(self, weight: float):
        super().__init__(weight)
        self.name = "Aggressive_Volume_Detector"
        # Aggressive 전략은 민감한 설정 사용
        self.volume_surge_threshold = 1.3  # 더 낮은 임계값 (기본 1.5 → 1.3)
        self.volume_trend_days = 2  # 더 짧은 기간 (기본 3 → 2)
        self.volume_confirmation_required = False  # 거래량 확인 불필요
    
    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """공격적인 거래량 신호를 감지합니다."""
        
        # 근거 수집 초기화
        self.technical_evidences = []
        
        if not self.validate_required_columns(df, self.required_columns):
            return 0.0, 0.0, [], []
        
        latest_data = df.iloc[-1]
        prev_data = df.iloc[-2]
        
        buy_score = 0.0
        sell_score = 0.0
        buy_details = []
        sell_details = []
        
        # 조정 계수 가져오기 (Aggressive는 강한 조정)
        volume_adj = self.get_adjustment_factor(market_trend, "volume_adj")
        
        # 거래량 급증 (낮은 임계값 사용)
        volume_ratio = latest_data['Volume'] / latest_data['Volume_SMA_20']
        
        if volume_ratio > self.volume_surge_threshold:
            # 거래량 급증 강도 계산 (더 민감한 범위)
            volume_strength = min((volume_ratio - self.volume_surge_threshold) / self.volume_surge_threshold, 1.5)
            
            # 상승 시 거래량 급증
            if latest_data['Close'] > prev_data['Close']:
                # 상승폭에 따른 추가 가중치 (더 민감한 범위)
                price_change_pct = (latest_data['Close'] - prev_data['Close']) / prev_data['Close']
                price_strength = min(price_change_pct * 150, 2.0)  # 최대 2% 상승까지
                
                buy_score += self.weight * volume_adj * (1.2 + volume_strength + price_st 