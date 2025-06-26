"""
Analysis Configuration Module - 새로운 구조

🎯 명확한 설정 파일 구조:
├── indicators.py           (기술적 지표 계산 설정)
├── signals.py             (신호 감지 및 실시간 분석 설정)
├── dynamic_strategies.py  (동적 전략 + 모디파이어)
└── static_strategies.py   (정적 전략 호환성용)

✅ 혜택:
- 명확한 책임 분리
- 중복 제거
- 직관적인 파일명
- 유지보수성 대폭 향상
"""

# 새로운 구조의 설정들
from .indicators import *
from .signals import *
from .dynamic_strategies import *
from .static_strategies import *
