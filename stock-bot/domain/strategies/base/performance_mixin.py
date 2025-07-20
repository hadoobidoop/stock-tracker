"""
전략 성능 모니터링 Mixin - 전략의 성능 추적 기능을 제공
"""

from datetime import datetime
from typing import Dict, Any


class PerformanceMixin:
    """전략 성능 모니터링 기능을 제공하는 Mixin 클래스"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 성능 모니터링 변수들 초기화
        if not hasattr(self, 'signals_generated'):
            self.signals_generated = 0
        if not hasattr(self, 'last_analysis_time'):
            self.last_analysis_time = None
        if not hasattr(self, 'average_score'):
            self.average_score = 0.0
        if not hasattr(self, 'score_history'):
            self.score_history = []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """전략 성능 지표 반환"""
        # 속성이 없는 경우 기본값으로 초기화
        if not hasattr(self, 'signals_generated'):
            self.signals_generated = 0
        if not hasattr(self, 'average_score'):
            self.average_score = 0.0
        if not hasattr(self, 'last_analysis_time'):
            self.last_analysis_time = None
        if not hasattr(self, 'score_history'):
            self.score_history = []
            
        return {
            'signals_generated': self.signals_generated,
            'average_score': self.average_score,
            'last_analysis_time': self.last_analysis_time,
            'score_history_length': len(self.score_history),
            'is_initialized': getattr(self, 'is_initialized', False),
            'signal_threshold': getattr(self.config, 'signal_threshold', 0),
            'risk_per_trade': getattr(self.config, 'risk_per_trade', 0)
        }

    def reset_performance_metrics(self):
        """성능 지표 초기화"""
        self.signals_generated = 0
        self.score_history.clear()
        self.average_score = 0.0
        self.last_analysis_time = None
    
    def _update_performance_metrics(self, score: float):
        """성능 지표 업데이트 (내부 사용)"""
        self.signals_generated += 1
        self.score_history.append(score)
        self.average_score = sum(self.score_history) / len(self.score_history)
        self.last_analysis_time = datetime.now()
    
    def _track_analysis_time(self):
        """분석 시간 추적 (내부 사용)"""
        self.last_analysis_time = datetime.now()