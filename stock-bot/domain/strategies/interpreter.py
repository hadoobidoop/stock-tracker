"""
YAML 전략 해석기 (Strategy Interpreter)

YAML 파일로 정의된 전략을 읽어서 실행 가능한 전략 객체를 동적으로 생성합니다.
Phase 2에서 만든 analysis, rules, detectors 모듈들을 활용합니다.
"""

import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from domain.signals.models import StrategyResult, TradingSignal
from domain.signals.models.enums import StrategyType, TradeType
from infrastructure.db.models.enums import TrendType
from domain.signals.rules import RULES
from domain.signals.detectors.trend_following.sma_detector import SMASignalDetector
from domain.signals.detectors.trend_following.macd_detector import MACDSignalDetector
from domain.signals.detectors.volume.volume_detector import VolumeSignalDetector
from domain.signals.detectors.composite.composite_detector import CompositeSignalDetector

logger = logging.getLogger(__name__)


@dataclass
class YAMLStrategyConfig:
    """YAML에서 로드한 전략 설정"""
    strategy_info: Dict[str, Any]
    signal_config: Dict[str, Any]
    position_management: Dict[str, Any]
    risk_management: Dict[str, Any]
    detectors: Dict[str, Any]
    trading_rules: Dict[str, Any]
    market_filters: Dict[str, Any]
    mode_overrides: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class YAMLStrategyInterpreter:
    """YAML 전략 해석기"""
    
    def __init__(self, strategies_path: str = "domain/strategies/definitions"):
        self.strategies_path = Path(strategies_path)
        self.loaded_strategies: Dict[str, YAMLStrategyConfig] = {}
        
    def load_strategy(self, strategy_name: str) -> YAMLStrategyConfig:
        """
        YAML 파일에서 전략을 로드합니다.
        
        Args:
            strategy_name: 전략명 (파일명에서 .yml 제외)
            
        Returns:
            YAMLStrategyConfig: 로드된 전략 설정
        """
        if strategy_name in self.loaded_strategies:
            return self.loaded_strategies[strategy_name]
            
        yaml_file = self.strategies_path / f"{strategy_name}.yml"
        if not yaml_file.exists():
            raise FileNotFoundError(f"전략 파일을 찾을 수 없습니다: {yaml_file}")
            
        with open(yaml_file, 'r', encoding='utf-8') as f:
            strategy_data = yaml.safe_load(f)
            
        config = YAMLStrategyConfig(
            strategy_info=strategy_data.get('strategy_info', {}),
            signal_config=strategy_data.get('signal_config', {}),
            position_management=strategy_data.get('position_management', {}),
            risk_management=strategy_data.get('risk_management', {}),
            detectors=strategy_data.get('detectors', {}),
            trading_rules=strategy_data.get('trading_rules', {}),
            market_filters=strategy_data.get('market_filters', {}),
            mode_overrides=strategy_data.get('mode_overrides'),
            metadata=strategy_data.get('metadata')
        )
        
        self.loaded_strategies[strategy_name] = config
        return config
        
    def create_strategy(self, strategy_name: str) -> 'YAMLBasedStrategy':
        """
        YAML 설정으로부터 전략 인스턴스를 생성합니다.
        
        Args:
            strategy_name: 전략명
            
        Returns:
            YAMLBasedStrategy: 생성된 전략 인스턴스
        """
        config = self.load_strategy(strategy_name)
        return YAMLBasedStrategy(strategy_name, config, self)
        
    def create_detectors(self, detector_configs: Dict[str, Any]) -> List:
        """
        YAML 설정으로부터 detector 인스턴스들을 생성합니다.
        
        Args:
            detector_configs: detector 설정 딕셔너리
            
        Returns:
            List: 생성된 detector 인스턴스들
        """
        detectors = []
        
        # SMA Detector
        if detector_configs.get('sma', {}).get('enabled', False):
            sma_config = detector_configs['sma']
            detectors.append(SMASignalDetector(
                weight=sma_config['weight'],
                name=f"YAML_SMA_Detector",
                parameters=sma_config.get('parameters', {})
            ))
            
        # MACD Detector
        if detector_configs.get('macd', {}).get('enabled', False):
            macd_config = detector_configs['macd']
            detectors.append(MACDSignalDetector(
                weight=macd_config['weight'],
                name=f"YAML_MACD_Detector",
                parameters=macd_config.get('parameters', {})
            ))
            
        # Volume Detector
        if detector_configs.get('volume', {}).get('enabled', False):
            volume_config = detector_configs['volume']
            detectors.append(VolumeSignalDetector(
                weight=volume_config['weight'],
                name=f"YAML_Volume_Detector",
                parameters=volume_config.get('parameters', {})
            ))
            
        # Composite Detector
        if detector_configs.get('composite', {}).get('enabled', False):
            composite_config = detector_configs['composite']
            # CompositeDetector는 하위 detector들이 필요하므로 현재는 생략
            # 필요한 경우 별도로 구현
            logger.info("CompositeDetector는 현재 YAML에서 지원하지 않습니다.")
            
        return detectors
        
    def evaluate_trading_rules(self, rules_config: Dict[str, Any], data: pd.DataFrame) -> Tuple[float, float]:
        """
        YAML에 정의된 매매 규칙들을 평가합니다.
        
        Args:
            rules_config: 매매 규칙 설정
            data: 시장 데이터
            
        Returns:
            Tuple[float, float]: (매수 신호 점수, 매도 신호 점수)
        """
        buy_score = 0.0
        sell_score = 0.0
        
        # 매수 규칙 평가
        buy_conditions = rules_config.get('buy_conditions', [])
        for condition in buy_conditions:
            rule_name = condition['rule']
            weight = condition.get('weight', 1.0)
            required = condition.get('required', False)
            
            if rule_name in RULES:
                try:
                    result = RULES[rule_name](data)
                    if result:
                        buy_score += weight
                    elif required:
                        # 필수 조건이 만족되지 않으면 매수 신호 0
                        buy_score = 0.0
                        break
                except Exception as e:
                    print(f"규칙 평가 오류 ({rule_name}): {e}")
                    
        # 매도 규칙 평가
        sell_conditions = rules_config.get('sell_conditions', [])
        for condition in sell_conditions:
            rule_name = condition['rule']
            weight = condition.get('weight', 1.0)
            
            if rule_name in RULES:
                try:
                    result = RULES[rule_name](data)
                    if result:
                        sell_score += weight
                except Exception as e:
                    print(f"규칙 평가 오류 ({rule_name}): {e}")
                    
        return buy_score, sell_score


class YAMLBasedStrategy:
    """YAML 기반 동적 전략"""
    
    def __init__(self, strategy_name: str, config: YAMLStrategyConfig, interpreter: YAMLStrategyInterpreter):
        self.strategy_name = strategy_name
        self.config = config
        self.interpreter = interpreter
        
        # Detector 인스턴스들 생성
        self.detectors = interpreter.create_detectors(config.detectors)
        
        # 전략 타입 결정 (메타데이터 기반)
        self.strategy_type = self._determine_strategy_type()
        
    def _determine_strategy_type(self) -> StrategyType:
        """메타데이터나 설정을 기반으로 전략 타입을 결정합니다."""
        tags = self.config.metadata.get('tags', []) if self.config.metadata else []
        
        if 'conservative' in tags:
            return StrategyType.CONSERVATIVE
        elif 'aggressive' in tags:
            return StrategyType.AGGRESSIVE
        elif 'momentum' in tags:
            return StrategyType.MOMENTUM
        elif 'trend_following' in tags:
            return StrategyType.TREND_FOLLOWING
        else:
            return StrategyType.BALANCED
            
    def analyze(self, data: pd.DataFrame, symbol: str = "UNKNOWN") -> StrategyResult:
        """
        전략 분석을 수행합니다.
        
        Args:
            data: 시장 데이터
            symbol: 심볼명
            
        Returns:
            StrategyResult: 분석 결과
        """
        try:
            # 1. Detector들로부터 신호 점수 수집
            detector_score = 0.0
            detector_signals = []
            
            for detector in self.detectors:
                try:
                    # detector.detect_signals 호출 (올바른 인터페이스)
                    buy_score, sell_score, buy_details, sell_details = detector.detect_signals(
                        data, 
                        market_trend=TrendType.NEUTRAL,  # 기본값
                        long_term_trend=TrendType.NEUTRAL,  # 기본값
                        daily_extra_indicators={}  # 기본값
                    )
                    
                    # 매수/매도 점수 중 더 높은 것을 사용
                    if buy_score > sell_score:
                        detector_score += buy_score * detector.weight
                        detector_signals.extend(buy_details)
                    elif sell_score > 0:
                        detector_score -= sell_score * detector.weight  # 매도는 음수로
                        detector_signals.extend(sell_details)
                        
                except Exception as e:
                    logger.warning(f"Detector 오류 ({detector.name}): {e}")
                    
            # 2. YAML 규칙 기반 추가 점수 계산
            rules_buy_score, rules_sell_score = self.interpreter.evaluate_trading_rules(
                self.config.trading_rules, data
            )
            
            # 3. 전체 신호 점수 계산
            total_score = detector_score + rules_buy_score - rules_sell_score
            
            # 4. 설정된 배수 적용
            score_multiplier = self.config.signal_config.get('score_multiplier', 1.0)
            final_score = total_score * score_multiplier
            
            # 5. 임계값 비교하여 신호 결정
            threshold = self.config.signal_config.get('threshold', 8.0)
            
            if final_score >= threshold:
                signal = TradeType.BUY
            elif final_score <= -threshold:
                signal = TradeType.SELL
            else:
                signal = TradeType.HOLD
                
            # 6. TradingSignal 생성
            trading_signal = TradingSignal(
                symbol=symbol,
                signal=signal,
                confidence=min(abs(final_score) / threshold, 1.0),
                timestamp=data.index[-1] if not data.empty else pd.Timestamp.now(),
                evidence=f"YAML 전략 {self.strategy_name}: detector_score={detector_score:.2f}, rules_score={rules_buy_score-rules_sell_score:.2f}",
                metadata={
                    'detector_signals': len(detector_signals),
                    'rules_buy_score': rules_buy_score,
                    'rules_sell_score': rules_sell_score,
                    'score_multiplier': score_multiplier
                }
            )
            
            return StrategyResult(
                strategy_name=self.strategy_name,
                strategy_type=self.strategy_type,
                signal=trading_signal,
                confidence=trading_signal.confidence,
                score=final_score,
                evidence=[trading_signal.evidence],
                metadata={
                    'yaml_config': True,
                    'threshold': threshold,
                    'detector_count': len(self.detectors),
                    'active_rules': len(self.config.trading_rules.get('buy_conditions', [])) + len(self.config.trading_rules.get('sell_conditions', []))
                }
            )
            
        except Exception as e:
            # 오류 발생 시 기본 HOLD 신호 반환
            return StrategyResult(
                strategy_name=self.strategy_name,
                strategy_type=self.strategy_type,
                signal=TradingSignal(
                    symbol=symbol,
                    signal=TradeType.HOLD,
                    confidence=0.0,
                    timestamp=pd.Timestamp.now(),
                    evidence=f"YAML 전략 오류: {str(e)}"
                ),
                confidence=0.0,
                score=0.0,
                evidence=[f"전략 분석 중 오류 발생: {str(e)}"],
                metadata={'error': True, 'error_message': str(e)}
            )
            
    def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보를 반환합니다."""
        return {
            **self.config.strategy_info,
            'strategy_type': self.strategy_type.value,
            'detector_count': len(self.detectors),
            'yaml_based': True
        }