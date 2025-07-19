"""
정적 전략 설정 (확장된 버전) - DEPRECATED

⚠️  이 파일은 더 이상 사용되지 않습니다 (DEPRECATED)
⚠️  각 전략별 개별 config 파일로 이관 완료

=== 이관 완료된 전략들 ===
✅ CONSERVATIVE          → domain/strategies/conservative/configs/conservative_config.py
✅ BALANCED              → domain/strategies/balanced/configs/balanced_config.py
✅ AGGRESSIVE            → domain/strategies/aggressive/configs/aggressive_config.py
✅ MOMENTUM              → domain/strategies/momentum/configs/momentum_config.py
✅ TREND_FOLLOWING       → domain/strategies/trend_following/configs/trend_following_config.py
✅ SCALPING              → domain/strategies/scalping/configs/scalping_config.py
✅ SWING                 → domain/strategies/swing/configs/swing_config.py
✅ MEAN_REVERSION        → domain/strategies/mean_reversion/configs/mean_reversion_config.py
✅ TREND_PULLBACK        → domain/strategies/trend_pullback/configs/trend_pullback_config.py
✅ VOLATILITY_BREAKOUT   → domain/strategies/volatility_breakout/configs/volatility_breakout_config.py
✅ MULTI_TIMEFRAME       → domain/strategies/multi_timeframe/configs/multi_timeframe_config.py
✅ ADAPTIVE_MOMENTUM     → domain/strategies/adaptive_momentum_hybrid/configs/adaptive_momentum_hybrid_config.py
✅ CONSERVATIVE_REVERSION_HYBRID → domain/strategies/conservative_reversion_hybrid/configs/conservative_reversion_hybrid_config.py
✅ MARKET_REGIME_HYBRID  → domain/strategies/market_regime_hybrid/configs/market_regime_hybrid_config.py

향후 새로운 전략 설정은 각 전략 폴더의 configs/ 디렉토리에 개별 파일로 생성하세요.
기존 정적 전략들을 모두 유지하면서 동적 전략 시스템과 호환되도록 구성
"""

from typing import Dict, Any, List
from domain.analysis.base.models import StrategyConfig, DetectorConfig
from domain.analysis.base.models.enums import StrategyType



STRATEGY_CONFIGS = {
    # === 기본 3가지 전략 ===
    StrategyType.CONSERVATIVE: StrategyConfig(
        name="보수적 전략",
        description="높은 신뢰도의 강한 신호만 사용하는 안전한 전략",
        signal_threshold=12.0,  # 높은 임계값
        risk_per_trade=0.01,    # 1% 리스크
        implementation_class="domain.strategies.conservative.conservative_strategy.ConservativeStrategy",
        market_filters={
            "trend_alignment": True,
            "volume_confirmation": True
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 672  # 28일
        }
    ),
    
    StrategyType.BALANCED: StrategyConfig(
        name="균형잡힌 전략",
        description="다양한 신호를 균형있게 사용하는 기본 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.balanced_strategy.BalancedStrategy",
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 5,
            "position_timeout_hours": 504  # 21일
        }
    ),
    
    StrategyType.AGGRESSIVE: StrategyConfig(
        name="공격적 전략",
        description="낮은 임계값으로 많은 거래 기회를 포착하는 전략",
        signal_threshold=5.0,   # 낮은 임계값
        risk_per_trade=0.03,    # 3% 리스크
        implementation_class="domain.analysis.strategy.implementations.aggressive_strategy.AggressiveStrategy",
        market_filters={
            "trend_alignment": False,
            "volume_confirmation": False
        },
        position_management={
            "max_positions": 8,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    # === 확장 정적 전략들 ===
    StrategyType.MOMENTUM: StrategyConfig(
        name="모멘텀 전략",
        description="RSI, 스토캐스틱 등 모멘텀 지표 중심 전략",
        signal_threshold=6.0,
        risk_per_trade=0.025,
        implementation_class="domain.strategies.momentum.momentum_strategy.MomentumStrategy",
        market_filters={
            "momentum_confirmation": True
        },
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 336
        }
    ),
    
    StrategyType.TREND_FOLLOWING: StrategyConfig(
        name="추세추종 전략",
        description="SMA, MACD, ADX 등 추세 지표 중심 전략",
        signal_threshold=7.0,
        risk_per_trade=0.02,
        implementation_class="domain.strategies.trend_following.trend_following_strategy.TrendFollowingStrategy",
        market_filters={
            "trend_alignment": True,
            "trend_strength": True
        },
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 720
        }
    ),
    
    StrategyType.SCALPING: StrategyConfig(
        name="스캘핑 전략",
        description="빠른 진입/청산을 위한 단기 전략",
        signal_threshold=4.0,   # 매우 낮은 임계값
        risk_per_trade=0.01,    # 낮은 리스크
        implementation_class="domain.strategies.scalping.scalping_strategy.ScalpingStrategy",
        market_filters={
            "volume_confirmation": True,
            "volatility_filter": True
        },
        position_management={
            "max_positions": 10,
            "position_timeout_hours": 4   # 4시간만 보유
        }
    ),
    
    StrategyType.SWING: StrategyConfig(
        name="스윙 전략",
        description="중기 추세 변화를 포착하는 전략",
        signal_threshold=7.0,
        risk_per_trade=0.025,
        implementation_class="domain.strategies.swing.swing_strategy.SwingStrategy",
        market_filters={
            "trend_alignment": False
        },
        position_management={
            "max_positions": 3,
            "position_timeout_hours": 336  # 14일
        }
    ),
    
    StrategyType.MEAN_REVERSION: StrategyConfig(
        name="평균 회귀 전략",
        description="과매수/과매도 후 평균으로 회귀하는 경향을 이용하는 전략",
        signal_threshold=7.0,
        risk_per_trade=0.015,
        implementation_class="domain.strategies.mean_reversion.mean_reversion_strategy.MeanReversionStrategy",
        market_filters={},
        position_management={
            "max_positions": 4,
            "position_timeout_hours": 24
        }
    ),
    
    StrategyType.TREND_PULLBACK: StrategyConfig(
        name="추세 추종 눌림목 전략",
        description="상승 추세 중 일시적 하락(눌림목) 시 매수하는 전략",
        signal_threshold=8.0,
        risk_per_trade=0.02,
        implementation_class="domain.strategies.trend_pullback.trend_pullback_strategy.TrendPullbackStrategy",
        market_filters={"trend_alignment": True},
        position_management={"max_positions": 4, "position_timeout_hours": 120}
    ),
    
    StrategyType.VOLATILITY_BREAKOUT: StrategyConfig(
        name="변동성 돌파 전략",
        description="변동성 응축 후 폭발하는 시점을 포착하는 전략",
        signal_threshold=6.0,
        risk_per_trade=0.025,
        implementation_class="domain.strategies.volatility_breakout.volatility_breakout_strategy.VolatilityBreakoutStrategy",
        market_filters={"volume_confirmation": True},
        position_management={"max_positions": 3, "position_timeout_hours": 48}
    ),
    
    StrategyType.MULTI_TIMEFRAME: StrategyConfig(
        name="다중 시간대 확인 전략",
        description="장기 추세(일봉)와 단기(시간봉) 진입 신호를 함께 확인하는 전략",
        signal_threshold=9.0,
        risk_per_trade=0.02,
        implementation_class="domain.analysis.strategy.implementations.multi_timeframe_strategy.MultiTimeframeStrategy",
        market_filters={"multi_timeframe_confirmation": True},
        position_management={"max_positions": 3, "position_timeout_hours": 504}
    ),
    
    StrategyType.ADAPTIVE_MOMENTUM: StrategyConfig(
        name="적응형 모멘텀",
        description="추세, 모멘텀, 변동성을 결합한 적응형 전략",
        signal_threshold=6.0,
        risk_per_trade=0.02,
        implementation_class="domain.strategies.adaptive_momentum_hybrid.adaptive_momentum_hybrid_strategy.AdaptiveMomentumStrategy",
        market_filters={},
        position_management={}
    ),

    StrategyType.CONSERVATIVE_REVERSION_HYBRID: StrategyConfig(
        name="보수적 평균 회귀 하이브리드",
        description="보수적 추세 확인 후 평균 회귀로 진입하는 전략",
        signal_threshold=6.0, # 임계값을 약간 낮춰 더 많은 기회 포착
        risk_per_trade=0.015,
        implementation_class="domain.strategies.conservative_reversion_hybrid.conservative_reversion_hybrid_strategy.ConservativeReversionHybridStrategy",
        market_filters={},
        position_management={}
    ),

    StrategyType.MARKET_REGIME_HYBRID: StrategyConfig(
        name="시장 체제 적응 하이브리드",
        description="시장 추세/변동성에 따라 하위 전략을 동적으로 선택",
        signal_threshold=6.0, # 하위 전략의 임계값을 따름
        risk_per_trade=0.02,
        implementation_class="domain.strategies.market_regime_hybrid.market_regime_hybrid_strategy.MarketRegimeHybridStrategy",
        market_filters={},
        position_management={}
    )
    # MACRO_DRIVEN config removed - functionality moved to dynamic strategy system
}


# ====================
# --- 호환성 함수들 ---
# ====================

def get_strategy_config(strategy_type: StrategyType) -> StrategyConfig:
    """전략 설정 조회"""
    return STRATEGY_CONFIGS.get(strategy_type)


def get_all_strategy_types() -> List[StrategyType]:
    """모든 전략 타입 반환"""
    return list(StrategyType)


def get_static_strategy_types() -> List[StrategyType]:
    """정적 전략 타입들만 반환 (동적 전략 제외)"""
    excluded = {StrategyType.DYNAMIC_WEIGHT, StrategyType.MACRO_DRIVEN}
    return [st for st in StrategyType if st not in excluded]


def get_available_strategies() -> Dict[str, List[str]]:
    """사용 가능한 전략들을 카테고리별로 반환"""
    return {
        "basic": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"],
        "momentum": ["MOMENTUM", "RSI_STOCH", "SCALPING"],
        "trend": ["TREND_FOLLOWING", "TREND_PULLBACK"],
        "reversion": ["MEAN_REVERSION", "SWING"],
        "advanced": ["VOLATILITY_BREAKOUT", "MULTI_TIMEFRAME"]
    }


def is_strategy_available(strategy_name: str) -> bool:
    """전략 사용 가능 여부 확인"""
    try:
        strategy_type = StrategyType(strategy_name.lower())
        return strategy_type in STRATEGY_CONFIGS
    except ValueError:
        return False


# ==============================================
# ⚠️  DEPRECATION WARNING
# ==============================================

import warnings

def show_deprecation_warning():
    """
    이 파일이 deprecated 되었음을 알리는 경고 메시지 출력
    """
    warnings.warn(
        "\n"
        "⚠️  static_strategies.py는 더 이상 사용되지 않습니다!\n"
        "⚠️  각 전략의 개별 config 파일을 사용해주세요.\n"
        "\n"
        "예시:\n"
        "  from domain.strategies.conservative.configs import ConservativeStrategyConfig\n"
        "  from domain.strategies.aggressive.configs import AggressiveStrategyConfig\n"
        "\n"
        "자세한 내용은 CLAUDE.md 파일을 참조하세요.\n",
        DeprecationWarning,
        stacklevel=2
    )

# 자동으로 deprecation warning 표시 (import 시)
show_deprecation_warning() 