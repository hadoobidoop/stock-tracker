# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- Start the full system with scheduler: `python main.py`
- Run backtesting only: `python run_backtest.py --strategy CONSERVATIVE --tickers AAPL --start-date 2024-01-01 --end-date 2025-01-01`
- Compare multiple strategies: `python run_backtest.py --compare CONSERVATIVE AGGRESSIVE --tickers TSLA --start-date 2024-01-01`

### Testing
- Run all tests: `pytest`
- Run specific test file: `pytest tests/test_signal_evidence.py`
- Tests are located in `tests/` directory with pattern `test_*.py`

### Data Management
- Backfill market data: `python -m domain.market_data_backfiller.backfiller --start_date 2023-01-01 --end_date 2023-12-31`
- Backfill specific indicators: `python -m domain.market_data_backfiller.backfiller --start_date 2024-01-01 --indicators VIX BUFFETT_INDICATOR`

## Architecture Overview

This is a sophisticated stock analysis and trading signal detection system built with Domain-Driven Design (DDD) principles:

### Core Architecture
- **Domain Layer** (`domain/`): Business logic and core entities
- **Infrastructure Layer** (`infrastructure/`): Technical implementations (DB, API clients, logging, scheduling)
- **Common Layer** (`common/`): Shared utilities and configurations

### Key Domain Components

#### Analysis Engine (`domain/analysis/`)
Multi-layered technical analysis system that processes raw data through several stages:
1. **Signal Detection**: Individual technical indicators (RSI, MACD, SMA, etc.)
2. **Signal Orchestration**: Combines multiple signals with weighted scoring
3. **Strategy Engine**: Applies trading strategies to generate BUY/SELL decisions

#### Strategy System (`domain/strategies/`)
**IMPORTANT**: All strategies are now organized in independent packages under `domain/strategies/strategy_name/`:
- Each strategy folder contains: implementation, detectors, and configs
- Examples: `domain/strategies/conservative/`, `domain/strategies/aggressive/`
- Old `domain/analysis/strategy/implementations/` is deprecated

Three strategy modes:
1. **Static Strategies**: Single predefined strategy (e.g., MOMENTUM, CONSERVATIVE)
2. **Strategy Mix**: Ensemble of multiple strategies with voting mechanisms
3. **Dynamic Strategies**: Adaptive strategies that modify behavior based on market conditions

#### Backtesting Engine (`domain/backtesting/`)
Comprehensive strategy validation system with key performance indicators:
- Total Return, Annualized Return, Max Drawdown
- Sharpe Ratio, Win Rate, Profit Factor
- Results saved to `backtest_results/` as JSON files

#### Stock Data Management (`domain/stock/`)
- Real-time and historical market data handling
- Multiple data providers (Yahoo Finance, FRED, Buffett Indicator, etc.)
- OHLCV data management with technical indicator calculation

### Database Integration
- SQLAlchemy ORM with MySQL backend
- Repository pattern for data persistence abstraction
- Models in `infrastructure/db/models/`
- Automatic schema creation via `create_db_and_tables()`

### Scheduler System
- APScheduler for automated tasks
- Jobs in `infrastructure/scheduler/jobs/`
- Handles daily/hourly market data updates and real-time signal detection

## Key Strategy Types

Available strategies (use with `--strategy` or `--compare` flags):
- **CONSERVATIVE**: High-confidence signals only, capital preservation focus
- **BALANCED**: Balanced risk/reward approach
- **AGGRESSIVE**: Captures weak signals for active trading
- **MOMENTUM**: RSI/Stochastic-based momentum detection
- **TREND_FOLLOWING**: SMA/MACD trend analysis
- **MEAN_REVERSION**: Bollinger Bands-based mean reversion
- **MARKET_REGIME_HYBRID**: Dynamic strategy selection based on market conditions
- **SCALPING**: Ultra-short-term trading with volume analysis

## Important Implementation Notes

### Strategy Development
- When adding new strategies, follow the modular structure in `domain/strategies/`
- Each strategy should have its own folder with implementation, detectors, and configs
- Reference existing strategies like `conservative/` or `balanced/` for structure

### Market Data Providers
- New market indicators require database schema updates (ENUM additions)
- Provider efficiency is critical - use bulk operations for data storage
- Market data backfiller handles historical data gaps

### Testing Strategy
- Signal detection logic is tested in `tests/test_signal_evidence.py`
- Job-based tests for scheduler functionality
- Always run `pytest` before committing strategy changes

### Code Conventions
- Domain-driven design with clear separation of concerns
- Repository pattern for data access
- Factory pattern for strategy instantiation
- Korean comments in README, English in code

## Common Issues and Troubleshooting

### Strategy Initialization Errors
If you encounter strategy initialization failures, check:

1. **Constructor Signature**: All strategy classes should accept `(strategy_type: StrategyType, config)` parameters
2. **Config Classes**: Strategy-specific config classes must have required fields (name, description, signal_threshold, risk_per_trade)
3. **detector_weights**: Config classes should implement detector_weights attribute or inherit properly
4. **StrategyType Enum**: Ensure all strategy types are defined in `static_strategies.py`

### Missing Strategy Types
When adding new strategies:
- Add enum value to `StrategyType` in `static_strategies.py`
- Add mapping in `STRATEGY_CLASS_MAP` in `strategy_factory.py`
- Implement proper config class with detector_weights
- Follow constructor pattern: `__init__(self, strategy_type: StrategyType, config)`

### Database Schema Updates
When adding new market indicators:
- Update `MarketIndicatorType` enum in database models
- Run schema migration to add new ENUM values
- Update provider configs in `market_data_backfiller/config.py`