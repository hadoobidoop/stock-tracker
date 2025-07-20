"""
Trading Service - 실시간 거래 유스케이스

실시간 거래 비즈니스 로직을 담당하는 서비스
StrategyService로부터 전략 정의를 받고, signals의 rules와 analysis를 사용하여 
최종 매매 신호를 생성합니다.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List

from domain.signals.rules import RULES
from .strategy_service import StrategyService, StrategyDefinition


# DetectorFactory import는 나중에 필요시 추가


class SignalType(Enum):
    """거래 신호 타입"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """거래 신호 결과"""
    signal: SignalType
    strength: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    reasons: List[str]
    strategy_name: str
    timestamp: Optional[str] = None


class TradingService:
    """실시간 거래 신호 생성 서비스"""
    
    def __init__(self, strategy_service: StrategyService, data_repository):
        self.strategy_service = strategy_service
        self.data_repo = data_repository
    
    def generate_signal_for_strategy(self, strategy_name: str, stock_code: str) -> Optional[TradingSignal]:
        """
        특정 전략과 종목에 대한 거래 신호 생성
        
        Args:
            strategy_name: 전략 이름
            stock_code: 종목 코드
            
        Returns:
            TradingSignal: 거래 신호 객체
        """
        # 전략 정의 조회
        strategy = self.strategy_service.get_strategy(strategy_name)
        if not strategy:
            return None
        
        # 시장 데이터 조회
        try:
            data = self.data_repo.get_latest_data(stock_code)
            if not data:
                return None
        except Exception as e:
            print(f"Failed to get market data for {stock_code}: {e}")
            return None
        
        # 시장 필터 적용
        if not self._check_market_filters(strategy, data):
            return TradingSignal(
                signal=SignalType.HOLD,
                strength=0.0,
                confidence=1.0,
                reasons=["Market filters not satisfied"],
                strategy_name=strategy_name
            )
        
        # 매수 신호 검사
        buy_signal = self._evaluate_buy_rules(strategy, data)
        
        # 매도 신호 검사
        sell_signal = self._evaluate_sell_rules(strategy, data)
        
        # 최종 신호 결정
        return self._determine_final_signal(strategy_name, buy_signal, sell_signal)
    
    def _check_market_filters(self, strategy: StrategyDefinition, data: Dict[str, Any]) -> bool:
        """시장 필터 조건 확인"""
        if not strategy.market_filters:
            return True
        
        filters = strategy.market_filters
        
        # 거래량 필터
        if 'min_volume' in filters:
            if data.get('volume', 0) < filters['min_volume']:
                return False
        
        # 가격 범위 필터
        if 'price_range' in filters:
            price = data.get('close', 0)
            price_range = filters['price_range']
            if price < price_range.get('min', 0) or price > price_range.get('max', float('inf')):
                return False
        
        # 변동성 필터
        if 'volatility_filter' in filters:
            # 여기서 변동성 계산 로직 구현
            pass
        
        return True
    
    def _evaluate_buy_rules(self, strategy: StrategyDefinition, data: Dict[str, Any]) -> Dict[str, Any]:
        """매수 규칙 평가"""
        total_weight = 0.0
        passed_weight = 0.0
        reasons = []
        
        for rule_config in strategy.buy_rules:
            rule_name = rule_config['name']
            rule_weight = rule_config.get('weight', 1.0)
            rule_params = rule_config.get('params', {})
            
            total_weight += rule_weight
            
            # 규칙 실행
            rule_func = RULES.get(rule_name)
            if rule_func:
                try:
                    if rule_func(data, **rule_params):
                        passed_weight += rule_weight
                        reasons.append(f"Buy rule '{rule_name}' passed")
                except Exception as e:
                    print(f"Error executing buy rule '{rule_name}': {e}")
            else:
                print(f"Warning: Unknown buy rule '{rule_name}'")
        
        strength = passed_weight / total_weight if total_weight > 0 else 0.0
        
        return {
            'strength': strength,
            'passed_weight': passed_weight,
            'total_weight': total_weight,
            'reasons': reasons
        }
    
    def _evaluate_sell_rules(self, strategy: StrategyDefinition, data: Dict[str, Any]) -> Dict[str, Any]:
        """매도 규칙 평가"""
        total_weight = 0.0
        passed_weight = 0.0
        reasons = []
        
        for rule_config in strategy.sell_rules:
            rule_name = rule_config['name']
            rule_weight = rule_config.get('weight', 1.0)
            rule_params = rule_config.get('params', {})
            
            total_weight += rule_weight
            
            # 규칙 실행
            rule_func = RULES.get(rule_name)
            if rule_func:
                try:
                    if rule_func(data, **rule_params):
                        passed_weight += rule_weight
                        reasons.append(f"Sell rule '{rule_name}' passed")
                except Exception as e:
                    print(f"Error executing sell rule '{rule_name}': {e}")
            else:
                print(f"Warning: Unknown sell rule '{rule_name}'")
        
        strength = passed_weight / total_weight if total_weight > 0 else 0.0
        
        return {
            'strength': strength,
            'passed_weight': passed_weight,
            'total_weight': total_weight,
            'reasons': reasons
        }
    
    def _determine_final_signal(self, strategy_name: str, buy_signal: Dict[str, Any], sell_signal: Dict[str, Any]) -> TradingSignal:
        """최종 거래 신호 결정"""
        buy_strength = buy_signal['strength']
        sell_strength = sell_signal['strength']
        
        all_reasons = buy_signal['reasons'] + sell_signal['reasons']
        
        # 매도 신호가 강한 경우
        if sell_strength > 0.6:  # 임계값은 전략별로 설정 가능하도록 개선 필요
            return TradingSignal(
                signal=SignalType.SELL,
                strength=sell_strength,
                confidence=min(sell_strength * 1.2, 1.0),
                reasons=sell_signal['reasons'],
                strategy_name=strategy_name
            )
        
        # 매수 신호가 강한 경우
        elif buy_strength > 0.7:  # 임계값은 전략별로 설정 가능하도록 개선 필요
            return TradingSignal(
                signal=SignalType.BUY,
                strength=buy_strength,
                confidence=min(buy_strength * 1.1, 1.0),
                reasons=buy_signal['reasons'],
                strategy_name=strategy_name
            )
        
        # 그 외에는 HOLD
        else:
            return TradingSignal(
                signal=SignalType.HOLD,
                strength=max(buy_strength, sell_strength),
                confidence=0.5,
                reasons=["Signal strength insufficient"] + all_reasons[:3],  # 상위 3개 이유만
                strategy_name=strategy_name
            )
    
    def generate_signals_for_multiple_strategies(self, strategy_names: List[str], stock_code: str) -> Dict[str, TradingSignal]:
        """여러 전략에 대해 동시 신호 생성"""
        results = {}
        
        for strategy_name in strategy_names:
            signal = self.generate_signal_for_strategy(strategy_name, stock_code)
            if signal:
                results[strategy_name] = signal
        
        return results
    
    def get_consensus_signal(self, strategy_names: List[str], stock_code: str) -> TradingSignal:
        """여러 전략의 컨센서스 신호 생성"""
        signals = self.generate_signals_for_multiple_strategies(strategy_names, stock_code)
        
        if not signals:
            return TradingSignal(
                signal=SignalType.HOLD,
                strength=0.0,
                confidence=0.0,
                reasons=["No valid signals"],
                strategy_name="consensus"
            )
        
        # 투표 방식으로 컨센서스 결정
        buy_votes = sum(1 for s in signals.values() if s.signal == SignalType.BUY)
        sell_votes = sum(1 for s in signals.values() if s.signal == SignalType.SELL)
        hold_votes = sum(1 for s in signals.values() if s.signal == SignalType.HOLD)
        
        total_votes = len(signals)
        
        # 가중 평균 강도 계산
        avg_strength = sum(s.strength for s in signals.values()) / len(signals)
        
        # 컨센서스 결정
        if buy_votes > sell_votes and buy_votes > hold_votes:
            consensus_signal = SignalType.BUY
            confidence = buy_votes / total_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            consensus_signal = SignalType.SELL
            confidence = sell_votes / total_votes
        else:
            consensus_signal = SignalType.HOLD
            confidence = hold_votes / total_votes
        
        return TradingSignal(
            signal=consensus_signal,
            strength=avg_strength,
            confidence=confidence,
            reasons=[f"Consensus from {len(signals)} strategies"],
            strategy_name="consensus"
        )