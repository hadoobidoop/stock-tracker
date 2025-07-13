# MultiTimeframe 전략 config (독립 모듈)
# ===================================
# - 다중 시간대 전략(MultiTimeframeStrategy)의 모든 파라미터/튜닝값을 관리
# - 신호 임계값, Detector 가중치, 시장 필터, 포지션 관리 등 전략 동작의 핵심 설정값 포함
# - config만 수정해 전략 튜닝/확장 가능 (예: detector_weights, 임계값, 포지션 제한 등)
# - 신규 Detector/필터 추가 시에도 이 파일에서 관리 권장

from domain.analysis.strategy.configs.static_strategies import StrategyType

MULTI_TIMEFRAME_CONFIG = {
    "name": "다중 시간대 확인 전략",  # 전략 이름
    "description": "장기 추세(일봉)와 단기(시간봉) 진입 신호를 함께 확인하는 전략",  # 전략 설명
    "signal_threshold": 9.0,  # 신호 발생 임계값(최종 점수 9.0 이상 시 신호)
    "risk_per_trade": 0.02,  # 거래당 리스크 비율(2%)
    "detector_weights": {
        "composite": 7.0  # 복합 Detector(일봉+시간봉 컨센서스) 가중치
    },
    "market_filters": {
        "multi_timeframe_confirmation": True  # 다중 시간대 컨펌 필터 활성화 여부
    },
    "position_management": {
        "max_positions": 3,  # 최대 동시 보유 포지션 수
        "position_timeout_hours": 504  # 포지션 최대 보유 시간(21일)
    },
    "strategy_type": StrategyType.MULTI_TIMEFRAME  # 전략 Enum 타입
} 