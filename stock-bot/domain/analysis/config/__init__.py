"""
Analysis Configuration Module - 기능별 패키지 구조

🎯 명확한 설정 파일 구조:
├── indicators/     (기술적 지표 계산 설정)
├── signals/        (신호 감지 및 실시간 분석 설정)
└── strategies/     (정적/동적 전략 및 조합 설정)

✅ 혜택:
- 명확한 책임 분리
- 직관적인 패키지 구조
- 유지보수성 대폭 향상
"""

from .indicators import *
from .signals import *
from .strategies import *
