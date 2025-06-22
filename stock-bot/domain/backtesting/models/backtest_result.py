from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from .trade import Trade
from .portfolio import Portfolio


@dataclass
class BacktestResult:
    """백테스팅 결과 모델"""
    
    # 기본 정보
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # 포트폴리오 정보
    portfolio: Portfolio
    
    # 거래 내역
    all_trades: List[Trade] = field(default_factory=list)
    
    # 성과 지표
    total_return_percent: float = 0.0
    annualized_return_percent: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # 거래 통계
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # 시간 분석
    average_holding_period_hours: float = 0.0
    
    # 포트폴리오 가치 시계열
    portfolio_values: List[Dict[str, Any]] = field(default_factory=list)
    
    # 전략별 분석
    strategy_performance: Dict[str, Any] = field(default_factory=dict)
    
    # 메타데이터
    backtest_settings: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_metrics(self) -> None:
        """성과 지표 계산"""
        if not self.all_trades:
            return
        
        # 기본 통계
        self.total_trades = len(self.all_trades)
        winning_trades = [t for t in self.all_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.all_trades if t.pnl and t.pnl < 0]
        
        self.winning_trades = len(winning_trades)
        self.losing_trades = len(losing_trades)
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        
        # 수익/손실 분석
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        self.average_win = total_wins / self.winning_trades if self.winning_trades > 0 else 0.0
        self.average_loss = total_losses / self.losing_trades if self.losing_trades > 0 else 0.0
        self.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 최대 승/패
        if winning_trades:
            self.largest_win = max(t.pnl for t in winning_trades)
        if losing_trades:
            self.largest_loss = min(t.pnl for t in losing_trades)  # 음수값
        
        # 수익률
        self.total_return_percent = ((self.final_capital - self.initial_capital) / self.initial_capital) * 100
        
        # 연환산 수익률
        days = (self.end_date - self.start_date).days
        if days > 0:
            self.annualized_return_percent = ((self.final_capital / self.initial_capital) ** (365.25 / days) - 1) * 100
        
        # 최대 낙폭
        self.max_drawdown_percent = self.portfolio.max_drawdown * 100
        
        # 평균 보유 기간
        valid_trades = [t for t in self.all_trades if t.holding_period_hours is not None]
        if valid_trades:
            self.average_holding_period_hours = sum(t.holding_period_hours for t in valid_trades) / len(valid_trades)
        
        # 샤프 비율 (간단한 계산)
        if self.portfolio_values:
            returns = []
            for i in range(1, len(self.portfolio_values)):
                prev_value = self.portfolio_values[i-1]['portfolio_value']
                curr_value = self.portfolio_values[i]['portfolio_value']
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)
            
            if returns:
                import statistics
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0
                
                if std_return > 0:
                    # 간단한 샤프 비율 (무위험 수익률 0 가정)
                    self.sharpe_ratio = (mean_return * 252) / (std_return * (252 ** 0.5))
                
                # 소르티노 비율 (하방 표준편차)
                negative_returns = [r for r in returns if r < 0]
                if negative_returns:
                    downside_std = statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0
                    if downside_std > 0:
                        self.sortino_ratio = (mean_return * 252) / (downside_std * (252 ** 0.5))
    
    def analyze_by_signal_strength(self) -> Dict[str, Dict]:
        """신호 강도별 성과 분석"""
        signal_analysis = {
            'weak': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0},
            'medium': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0}, 
            'strong': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0}
        }
        
        for trade in self.all_trades:
            if trade.entry_signal_score < 10:
                category = 'weak'
            elif trade.entry_signal_score < 15:
                category = 'medium'
            else:
                category = 'strong'
            
            signal_analysis[category]['trades'].append(trade)
        
        # 각 카테고리별 통계 계산
        for category, data in signal_analysis.items():
            trades = data['trades']
            if trades:
                winning = [t for t in trades if t.pnl and t.pnl > 0]
                data['win_rate'] = len(winning) / len(trades)
                data['avg_return'] = sum(t.pnl_percent for t in trades if t.pnl_percent) / len(trades)
        
        return signal_analysis
    
    def analyze_by_market_condition(self) -> Dict[str, Dict]:
        """시장 상황별 성과 분석"""
        market_analysis = {
            'BULLISH': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0},
            'BEARISH': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0},
            'NEUTRAL': {'trades': [], 'win_rate': 0.0, 'avg_return': 0.0}
        }
        
        for trade in self.all_trades:
            market_trend = trade.market_trend_at_entry or 'NEUTRAL'
            if market_trend in market_analysis:
                market_analysis[market_trend]['trades'].append(trade)
        
        # 각 시장 상황별 통계 계산
        for condition, data in market_analysis.items():
            trades = data['trades']
            if trades:
                winning = [t for t in trades if t.pnl and t.pnl > 0]
                data['win_rate'] = len(winning) / len(trades)
                data['avg_return'] = sum(t.pnl_percent for t in trades if t.pnl_percent) / len(trades)
        
        return market_analysis
    
    def analyze_by_holding_period(self) -> Dict[str, Dict]:
        """보유 기간별 성과 분석"""
        period_analysis = {
            'short': {'trades': [], 'description': '< 24시간'},  
            'medium': {'trades': [], 'description': '1-7일'},
            'long': {'trades': [], 'description': '> 7일'}
        }
        
        for trade in self.all_trades:
            if not trade.holding_period_hours:
                continue
                
            if trade.holding_period_hours < 24:
                category = 'short'
            elif trade.holding_period_hours < 168:  # 7일
                category = 'medium'
            else:
                category = 'long'
            
            period_analysis[category]['trades'].append(trade)
        
        # 각 기간별 통계 계산
        for period, data in period_analysis.items():
            trades = data['trades']
            if trades:
                winning = [t for t in trades if t.pnl and t.pnl > 0]
                data['win_rate'] = len(winning) / len(trades)
                data['avg_return'] = sum(t.pnl_percent for t in trades if t.pnl_percent) / len(trades)
                data['trade_count'] = len(trades)
        
        return period_analysis
    
    def get_monthly_performance(self) -> pd.DataFrame:
        """월별 성과 분석"""
        monthly_data = []
        
        # 포트폴리오 가치 데이터에서 월별 수익률 계산
        if self.portfolio_values:
            df = pd.DataFrame(self.portfolio_values)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['month'] = df['timestamp'].dt.to_period('M')
            
            monthly_returns = df.groupby('month').agg({
                'portfolio_value': ['first', 'last']
            }).reset_index()
            
            monthly_returns.columns = ['month', 'start_value', 'end_value']
            monthly_returns['return_percent'] = ((monthly_returns['end_value'] - monthly_returns['start_value']) / monthly_returns['start_value']) * 100
            
            return monthly_returns
        
        return pd.DataFrame()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'backtest_period': {
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
                'duration_days': (self.end_date - self.start_date).days
            },
            'capital': {
                'initial_capital': self.initial_capital,
                'final_capital': self.final_capital,
                'total_return_percent': self.total_return_percent,
                'annualized_return_percent': self.annualized_return_percent
            },
            'risk_metrics': {
                'max_drawdown_percent': self.max_drawdown_percent,
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio
            },
            'trade_statistics': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'average_win': self.average_win,
                'average_loss': self.average_loss,
                'largest_win': self.largest_win,
                'largest_loss': self.largest_loss,
                'average_holding_period_hours': self.average_holding_period_hours
            },
            'detailed_analysis': {
                'signal_strength_analysis': self.analyze_by_signal_strength(),
                'market_condition_analysis': self.analyze_by_market_condition(),
                'holding_period_analysis': self.analyze_by_holding_period()
            },
            'settings': self.backtest_settings
        } 