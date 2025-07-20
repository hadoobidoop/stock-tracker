"""
Technical Indicator Models

This module defines data models for technical indicators.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class IndicatorType(Enum):
    """Technical indicator types"""
    SMA = "SMA"
    RSI = "RSI" 
    MACD = "MACD"
    STOCHASTIC = "STOCHASTIC"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    ATR = "ATR"
    VOLUME_SMA = "VOLUME_SMA"
    ADX = "ADX"
    KELTNER_CHANNELS = "KELTNER_CHANNELS"
    FIBONACCI = "FIBONACCI"


class TrendDirection(Enum):
    """Trend direction enumeration"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH" 
    NEUTRAL = "NEUTRAL"


@dataclass
class IndicatorValue:
    """Represents a single indicator value with metadata"""
    
    # Basic information
    indicator_type: IndicatorType
    value: float
    timestamp: datetime
    
    # Optional metadata
    period: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    trend_direction: Optional[TrendDirection] = None
    
    # Additional context
    signal_strength: Optional[float] = None
    confidence: Optional[float] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate the indicator value after initialization"""
        if self.value is None or (isinstance(self.value, float) and self.value != self.value):  # NaN check
            raise ValueError(f"Invalid indicator value: {self.value}")
        
        if self.trend_direction and not isinstance(self.trend_direction, TrendDirection):
            raise ValueError(f"Invalid trend direction: {self.trend_direction}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'indicator_type': self.indicator_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'period': self.period,
            'parameters': self.parameters,
            'trend_direction': self.trend_direction.value if self.trend_direction else None,
            'signal_strength': self.signal_strength,
            'confidence': self.confidence,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndicatorValue':
        """Create from dictionary representation"""
        return cls(
            indicator_type=IndicatorType(data['indicator_type']),
            value=data['value'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            period=data.get('period'),
            parameters=data.get('parameters'),
            trend_direction=TrendDirection(data['trend_direction']) if data.get('trend_direction') else None,
            signal_strength=data.get('signal_strength'),
            confidence=data.get('confidence'),
            description=data.get('description')
        ) 