"""
YAML 기반 포트폴리오 관리 (Portfolio Manager)

YAML 전략 정의의 portfolio 섹션에 정의된 규칙을 해석하고 실행하는 로직을 구현합니다.
자금 관리, 포지션 관리, 리스크 관리 등을 담당합니다.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import pandas as pd

from domain.signals.models import TradingSignal
from domain.signals.models.enums import TradeType


@dataclass
class PortfolioConfig:
    """포트폴리오 설정"""
    # 포지션 관리
    max_positions: int
    position_hold_hours: int
    
    # 리스크 관리
    risk_per_trade: float
    stop_loss_percentage: float
    take_profit_percentage: float
    
    # 시장 필터
    market_filters: Dict[str, Any]
    
    @classmethod
    def from_yaml_config(cls, yaml_config: Dict[str, Any]) -> 'PortfolioConfig':
        """YAML 설정으로부터 포트폴리오 설정 생성"""
        return cls(
            max_positions=yaml_config.get('position_management', {}).get('max_positions', 5),
            position_hold_hours=yaml_config.get('position_management', {}).get('position_hold_hours', 168),
            risk_per_trade=yaml_config.get('risk_management', {}).get('risk_per_trade', 0.02),
            stop_loss_percentage=yaml_config.get('risk_management', {}).get('stop_loss_percentage', 5.0),
            take_profit_percentage=yaml_config.get('risk_management', {}).get('take_profit_percentage', 10.0),
            market_filters=yaml_config.get('market_filters', {})
        )


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    entry_price: float
    quantity: int
    entry_time: pd.Timestamp
    stop_loss_price: float
    take_profit_price: float
    strategy_name: str
    position_value: float


class PortfolioManager:
    """YAML 기반 포트폴리오 매니저"""
    
    def __init__(self, total_balance: float):
        self.total_balance = total_balance
        self.available_balance = total_balance
        self.positions: Dict[str, Position] = {}
        self.position_history: List[Dict[str, Any]] = []
        
    def get_order_size(self, config: PortfolioConfig, current_price: float) -> float:
        """
        YAML 설정에 따라 주문할 금액을 계산합니다.
        
        Args:
            config: 포트폴리오 설정
            current_price: 현재 가격
            
        Returns:
            float: 주문 금액
        """
        # 거래당 리스크에 따른 최대 주문 금액
        max_order_value = self.total_balance * config.risk_per_trade
        
        # 사용 가능한 잔액의 일부만 사용
        available_order_value = self.available_balance * 0.9  # 90%만 사용
        
        # 더 작은 값 선택
        order_value = min(max_order_value, available_order_value)
        
        # 최소 주문 금액 확인
        min_order_value = 1000  # 최소 1000원
        if order_value < min_order_value:
            return 0.0
            
        return order_value
        
    def calculate_position_size(self, order_value: float, entry_price: float, stop_loss_price: float) -> int:
        """
        포지션 크기를 계산합니다.
        
        Args:
            order_value: 주문 금액
            entry_price: 진입 가격
            stop_loss_price: 손절 가격
            
        Returns:
            int: 주문 수량
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0
            
        # 리스크 기반 포지션 크기 계산
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            return 0
            
        max_shares_by_risk = int(order_value / entry_price)
        
        return max_shares_by_risk
        
    def calculate_stop_loss_price(self, entry_price: float, signal_type: TradeType, 
                                  stop_loss_percentage: float) -> float:
        """
        손절 가격을 계산합니다.
        
        Args:
            entry_price: 진입 가격
            signal_type: 신호 타입 (매수/매도)
            stop_loss_percentage: 손절 비율
            
        Returns:
            float: 손절 가격
        """
        if signal_type == TradeType.BUY:
            return entry_price * (1 - stop_loss_percentage / 100)
        elif signal_type == TradeType.SELL:
            return entry_price * (1 + stop_loss_percentage / 100)
        else:
            return entry_price
            
    def calculate_take_profit_price(self, entry_price: float, signal_type: TradeType,
                                    take_profit_percentage: float) -> float:
        """
        익절 가격을 계산합니다.
        
        Args:
            entry_price: 진입 가격
            signal_type: 신호 타입 (매수/매도)
            take_profit_percentage: 익절 비율
            
        Returns:
            float: 익절 가격
        """
        if signal_type == TradeType.BUY:
            return entry_price * (1 + take_profit_percentage / 100)
        elif signal_type == TradeType.SELL:
            return entry_price * (1 - take_profit_percentage / 100)
        else:
            return entry_price
            
    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """
        손절 조건을 확인합니다.
        
        Args:
            position: 포지션 정보
            current_price: 현재 가격
            
        Returns:
            bool: 손절 필요 여부
        """
        if position.entry_price > position.stop_loss_price:  # 매수 포지션
            return current_price <= position.stop_loss_price
        else:  # 매도 포지션
            return current_price >= position.stop_loss_price
            
    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """
        익절 조건을 확인합니다.
        
        Args:
            position: 포지션 정보
            current_price: 현재 가격
            
        Returns:
            bool: 익절 필요 여부
        """
        if position.entry_price < position.take_profit_price:  # 매수 포지션
            return current_price >= position.take_profit_price
        else:  # 매도 포지션
            return current_price <= position.take_profit_price
            
    def check_position_timeout(self, position: Position, current_time: pd.Timestamp,
                               hold_hours: int) -> bool:
        """
        포지션 보유 시간 초과를 확인합니다.
        
        Args:
            position: 포지션 정보
            current_time: 현재 시간
            hold_hours: 최대 보유 시간
            
        Returns:
            bool: 시간 초과 여부
        """
        hold_duration = current_time - position.entry_time
        max_hold_duration = pd.Timedelta(hours=hold_hours)
        return hold_duration >= max_hold_duration
        
    def can_open_position(self, config: PortfolioConfig, symbol: str) -> bool:
        """
        새로운 포지션을 열 수 있는지 확인합니다.
        
        Args:
            config: 포트폴리오 설정
            symbol: 심볼명
            
        Returns:
            bool: 포지션 개설 가능 여부
        """
        # 최대 포지션 수 확인
        if len(self.positions) >= config.max_positions:
            return False
            
        # 같은 심볼에 이미 포지션이 있는지 확인
        if symbol in self.positions:
            return False
            
        # 충분한 잔액이 있는지 확인
        min_balance = self.total_balance * 0.1  # 10% 여유 자금 유지
        if self.available_balance <= min_balance:
            return False
            
        return True
        
    def apply_market_filters(self, config: PortfolioConfig, symbol: str, 
                             market_data: Dict[str, Any]) -> bool:
        """
        시장 필터를 적용하여 거래 가능 여부를 확인합니다.
        
        Args:
            config: 포트폴리오 설정
            symbol: 심볼명
            market_data: 시장 데이터
            
        Returns:
            bool: 거래 가능 여부
        """
        filters = config.market_filters
        
        # 최소 거래량 필터
        if filters.get('min_volume', {}).get('enabled', False):
            min_volume = filters['min_volume']['value']
            current_volume = market_data.get('volume', 0)
            if current_volume < min_volume:
                return False
                
        # 가격 범위 필터
        if filters.get('price_range', {}).get('enabled', False):
            min_price = filters['price_range'].get('min_price', 0)
            max_price = filters['price_range'].get('max_price', float('inf'))
            current_price = market_data.get('close', 0)
            if not (min_price <= current_price <= max_price):
                return False
                
        # 변동성 필터
        if filters.get('volatility', {}).get('enabled', False):
            min_atr_ratio = filters['volatility'].get('min_atr_ratio', 0)
            max_atr_ratio = filters['volatility'].get('max_atr_ratio', 1)
            atr_ratio = market_data.get('atr_ratio', 0)
            if not (min_atr_ratio <= atr_ratio <= max_atr_ratio):
                return False
                
        return True
        
    def open_position(self, config: PortfolioConfig, signal: TradingSignal,
                      current_price: float, strategy_name: str) -> Optional[Position]:
        """
        새로운 포지션을 엽니다.
        
        Args:
            config: 포트폴리오 설정
            signal: 거래 신호
            current_price: 현재 가격
            strategy_name: 전략명
            
        Returns:
            Optional[Position]: 생성된 포지션 (실패시 None)
        """
        if not self.can_open_position(config, signal.symbol):
            return None
            
        # 주문 금액 계산
        order_value = self.get_order_size(config, current_price)
        if order_value <= 0:
            return None
            
        # 손절/익절 가격 계산
        stop_loss_price = self.calculate_stop_loss_price(
            current_price, signal.signal, config.stop_loss_percentage
        )
        take_profit_price = self.calculate_take_profit_price(
            current_price, signal.signal, config.take_profit_percentage
        )
        
        # 포지션 크기 계산
        quantity = self.calculate_position_size(order_value, current_price, stop_loss_price)
        if quantity <= 0:
            return None
            
        # 실제 주문 금액 계산
        actual_order_value = quantity * current_price
        
        # 잔액 확인
        if actual_order_value > self.available_balance:
            return None
            
        # 포지션 생성
        position = Position(
            symbol=signal.symbol,
            entry_price=current_price,
            quantity=quantity,
            entry_time=signal.timestamp,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            strategy_name=strategy_name,
            position_value=actual_order_value
        )
        
        # 포지션 추가 및 잔액 업데이트
        self.positions[signal.symbol] = position
        self.available_balance -= actual_order_value
        
        return position
        
    def close_position(self, symbol: str, close_price: float, close_reason: str) -> Optional[Dict[str, Any]]:
        """
        포지션을 닫습니다.
        
        Args:
            symbol: 심볼명
            close_price: 종료 가격
            close_reason: 종료 사유
            
        Returns:
            Optional[Dict]: 종료된 포지션 정보
        """
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        
        # 손익 계산
        if position.entry_price < position.take_profit_price:  # 매수 포지션
            pnl = (close_price - position.entry_price) * position.quantity
        else:  # 매도 포지션
            pnl = (position.entry_price - close_price) * position.quantity
            
        # 잔액 업데이트
        close_value = position.quantity * close_price
        self.available_balance += close_value
        
        # 포지션 기록 저장
        position_record = {
            'symbol': symbol,
            'strategy_name': position.strategy_name,
            'entry_price': position.entry_price,
            'close_price': close_price,
            'quantity': position.quantity,
            'entry_time': position.entry_time,
            'close_time': pd.Timestamp.now(),
            'pnl': pnl,
            'pnl_percentage': (pnl / position.position_value) * 100,
            'close_reason': close_reason
        }
        
        self.position_history.append(position_record)
        
        # 포지션 제거
        del self.positions[symbol]
        
        return position_record
        
    def update_positions(self, config: PortfolioConfig, market_data: Dict[str, float],
                         current_time: pd.Timestamp) -> List[Dict[str, Any]]:
        """
        모든 포지션을 업데이트하고 필요시 종료합니다.
        
        Args:
            config: 포트폴리오 설정
            market_data: {symbol: current_price} 형태의 시장 데이터
            current_time: 현재 시간
            
        Returns:
            List[Dict]: 종료된 포지션들의 정보
        """
        closed_positions = []
        symbols_to_close = []
        
        for symbol, position in self.positions.items():
            current_price = market_data.get(symbol)
            if current_price is None:
                continue
                
            # 손절 확인
            if self.check_stop_loss(position, current_price):
                record = self.close_position(symbol, current_price, "stop_loss")
                if record:
                    closed_positions.append(record)
                    symbols_to_close.append(symbol)
                    continue
                    
            # 익절 확인
            if self.check_take_profit(position, current_price):
                record = self.close_position(symbol, current_price, "take_profit")
                if record:
                    closed_positions.append(record)
                    symbols_to_close.append(symbol)
                    continue
                    
            # 시간 초과 확인
            if self.check_position_timeout(position, current_time, config.position_hold_hours):
                record = self.close_position(symbol, current_price, "timeout")
                if record:
                    closed_positions.append(record)
                    symbols_to_close.append(symbol)
                    continue
                    
        return closed_positions
        
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        포트폴리오 현재 상태를 반환합니다.
        
        Returns:
            Dict: 포트폴리오 상태 정보
        """
        total_position_value = sum(pos.position_value for pos in self.positions.values())
        
        return {
            'total_balance': self.total_balance,
            'available_balance': self.available_balance,
            'invested_balance': total_position_value,
            'position_count': len(self.positions),
            'positions': {symbol: {
                'entry_price': pos.entry_price,
                'quantity': pos.quantity,
                'value': pos.position_value,
                'strategy': pos.strategy_name
            } for symbol, pos in self.positions.items()},
            'total_trades': len(self.position_history)
        }