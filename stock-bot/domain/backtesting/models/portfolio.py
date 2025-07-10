from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from .trade import Trade, TradeStatus, TradeType


@dataclass
class Portfolio:
    """백테스팅 포트폴리오 관리"""
    
    # 기본 설정
    initial_cash: float
    current_cash: float
    
    # 포지션 관리
    open_positions: Dict[str, Trade] = field(default_factory=dict)  # ticker -> Trade
    closed_trades: List[Trade] = field(default_factory=list)
    
    # 수수료 설정
    commission_rate: float = 0.001  # 0.1% 기본 수수료
    
    # 통계
    max_drawdown: float = 0.0
    peak_portfolio_value: float = 0.0
    
    def __post_init__(self):
        self.peak_portfolio_value = self.initial_cash
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """현재 포트폴리오 총 가치 계산"""
        total_value = self.current_cash
        
        for ticker, trade in self.open_positions.items():
            if ticker in current_prices:
                current_price = current_prices[ticker]
                pnl, _ = trade.get_current_pnl(current_price)
                position_value = trade.entry_price * trade.entry_quantity + pnl
                total_value += position_value
        
        return total_value
    
    def calculate_position_size(self, 
                              entry_price: float, 
                              risk_per_trade: float = 0.02,
                              stop_loss_price: Optional[float] = None) -> int:
        """포지션 크기 계산 (리스크 기반)"""
        if stop_loss_price is None:
            # 손절가가 없으면 포트폴리오의 2%만 리스크
            risk_amount = self.current_cash * risk_per_trade
            quantity = int(risk_amount / entry_price)
        else:
            # 손절가가 있으면 그에 맞춰 포지션 크기 계산
            risk_amount = self.current_cash * risk_per_trade
            risk_per_share = abs(entry_price - stop_loss_price)
            if risk_per_share > 0:
                quantity = int(risk_amount / risk_per_share)
            else:
                quantity = int(risk_amount / entry_price)
        
        # 최소 1주, 최대 가용 현금으로 제한
        max_quantity = int(self.current_cash / (entry_price * (1 + self.commission_rate)))
        return max(1, min(quantity, max_quantity))
    
    def can_open_position(self, entry_price: float, quantity: int) -> bool:
        """포지션 개설 가능 여부 확인"""
        required_cash = entry_price * quantity * (1 + self.commission_rate)
        return self.current_cash >= required_cash
    
    def open_position(self, trade: Trade) -> bool:
        """포지션 개설"""
        if trade.ticker in self.open_positions:
            return False  # 이미 포지션이 있음
        
        required_cash = trade.entry_price * trade.entry_quantity * (1 + self.commission_rate)
        
        if not self.can_open_position(trade.entry_price, trade.entry_quantity):
            return False
        
        # 현금 차감
        self.current_cash -= required_cash
        
        # 포지션 추가
        self.open_positions[trade.ticker] = trade
        
        return True
    
    def close_position(self, 
                      ticker: str, 
                      exit_timestamp: datetime,
                      exit_price: float,
                      exit_signal_details: Optional[List[str]] = None,
                      exit_signal_score: Optional[int] = None,
                      status: TradeStatus = TradeStatus.CLOSED) -> bool:
        """포지션 청산"""
        if ticker not in self.open_positions:
            return False
        
        trade = self.open_positions.pop(ticker)
        
        # 거래 청산 (수수료율 전달)
        trade.close_trade(
            exit_timestamp, 
            exit_price, 
            self.commission_rate,
            exit_signal_details, 
            exit_signal_score, 
            status
        )
        
        # 현금 회수
        # PnL은 이미 수수료가 반영되었으므로, 여기서는 수수료를 다시 계산하지 않고 PnL을 직접 더함
        # gross_proceeds = exit_price * trade.entry_quantity
        # commission = gross_proceeds * self.commission_rate
        # net_proceeds = gross_proceeds - commission
        
        # 올바른 현금 회수 로직: 초기 투자 원금 + PnL
        entry_value = trade.entry_price * trade.entry_quantity
        self.current_cash += (entry_value + trade.pnl)
        
        # 완료된 거래 기록
        self.closed_trades.append(trade)
        
        return True
    
    def check_stop_loss_take_profit(self, current_prices: Dict[str, float], current_timestamp: datetime) -> List[str]:
        """손절/익절 조건 확인 및 실행"""
        closed_tickers = []
        
        for ticker, trade in list(self.open_positions.items()):
            if ticker not in current_prices:
                continue
                
            current_price = current_prices[ticker]
            
            # 손절 확인
            if trade.is_stop_loss_triggered(current_price):
                self.close_position(
                    ticker, 
                    current_timestamp, 
                    trade.stop_loss_price,
                    ["손절매 실행"],
                    0,
                    TradeStatus.STOP_LOSS
                )
                closed_tickers.append(f"{ticker}_STOP_LOSS")
            
            # 익절 확인
            elif trade.is_take_profit_triggered(current_price):
                self.close_position(
                    ticker,
                    current_timestamp,
                    trade.take_profit_price,
                    ["익절매 실행"],
                    0,
                    TradeStatus.TAKE_PROFIT
                )
                closed_tickers.append(f"{ticker}_TAKE_PROFIT")
        
        return closed_tickers
    
    def update_drawdown(self, current_prices: Dict[str, float]) -> None:
        """최대 낙폭 업데이트"""
        current_value = self.get_portfolio_value(current_prices)
        
        if current_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_value
        
        if self.peak_portfolio_value > 0:
            drawdown = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value
            self.max_drawdown = max(self.max_drawdown, drawdown)
    
    def get_current_positions(self) -> Dict[str, Dict]:
        """현재 보유 포지션 정보"""
        positions = {}
        for ticker, trade in self.open_positions.items():
            positions[ticker] = {
                'entry_price': trade.entry_price,
                'quantity': trade.entry_quantity,
                'entry_timestamp': trade.entry_timestamp,
                'stop_loss_price': trade.stop_loss_price,
                'take_profit_price': trade.take_profit_price,
                'signal_score': trade.entry_signal_score
            }
        return positions
    
    def get_statistics(self) -> Dict:
        """포트폴리오 통계"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'profit_factor': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': self.max_drawdown
            }
        
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl and t.pnl < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        average_win = total_wins / win_count if win_count > 0 else 0.0
        average_loss = total_losses / loss_count if loss_count > 0 else 0.0
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        total_pnl = sum(t.pnl for t in self.closed_trades if t.pnl)
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'max_drawdown': self.max_drawdown,
            'return_percent': (total_pnl / self.initial_cash) * 100 if self.initial_cash > 0 else 0.0
        } 