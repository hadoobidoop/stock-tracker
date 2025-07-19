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

This is a sophisticated stock analysis and trading signal detection system built with Domain-Driven Design (DDD) principles. The system has undergone significant refactoring toward centralized strategy management and direct registry usage patterns.

### Core Architecture
- **Domain Layer** (`domain/`): Business logic and core entities
- **Infrastructure Layer** (`infrastructure/`): Technical implementations (DB, API clients, logging, scheduling)
- **Common Layer** (`common/`): Shared utilities and configurations

### Central Orchestration System

**StrategyRegistry** (`domain/orchestration/strategy_registry.py`): Central hub for all strategy information across static, dynamic, and mix strategies. The global instance `strategy_registry` is the single source of truth for strategy management.

**Key Pattern**: Direct registry access instead of delegation:
```python
# Use this pattern:
strategy_registry.get_strategy_config(strategy_name, "static")
strategy_registry.get_available_strategies("dynamic")["dynamic"]
strategy_registry.is_strategy_supported(strategy_identifier)

# Avoid delegation functions - they have been removed
```

**StrategyFactory** (`domain/orchestration/factory.py`): Creates strategy instances with proper dependency injection. Maps `StrategyType` enums to concrete classes via `STRATEGY_CLASS_MAP`.

**StrategyManager** (`domain/orchestration/manager.py`): Orchestrates multiple strategy types, manages active strategies and mode switching. Uses factory directly instead of delegation.

**StrategySelector** (`domain/orchestration/selector.py`): Utility layer for strategy selection, validation, and market condition-based recommendations.

### Signal Detection and Analysis Flow

**Three-Layer Architecture**:
1. **Individual Signal Detectors** (`domain/signals/detectors/`): Categories include momentum (RSI, Stochastic), trend_following (MACD, SMA), volatility (Bollinger Bands), volume
2. **Signal Orchestration** (`SignalDetectionOrchestrator`): Coordinates multiple detectors, calculates weighted scores, handles market trend adjustments
3. **Strategy Engine**: Individual strategies consume orchestrated signals and return standardized `StrategyResult` objects

**Flow**: `Raw Data → Technical Indicators → Signal Detectors → Signal Orchestrator → Strategy Analysis → StrategyResult`

### Strategy System Architecture

**Three Strategy Categories**:
1. **Static Strategies** (`domain/strategies/single/`): Independent packages per strategy (conservative/, aggressive/, balanced/, etc.). Each contains strategy.py, configs/, detectors/
2. **Dynamic Strategies** (`domain/strategies/dynamic/`): Adaptive strategies using `ModifierEngine` for real-time weight adjustments based on market conditions
3. **Strategy Mixes** (`domain/strategies/mixes/`): Ensemble approaches with weighted, voting, and ensemble combination modes

**Important**: Each strategy package is fully self-contained with no cross-strategy dependencies.

### Key Integration Points

**Backtesting Engine** (`domain/backtesting/`): Multi-strategy support with strategy-agnostic design. Supports single strategy analysis, strategy comparison, and mix testing.

**Database Integration**: SQLAlchemy ORM with MySQL backend, Repository pattern, models in `infrastructure/db/models/`, automatic schema creation via `create_db_and_tables()`.

**Scheduler System**: APScheduler for automated tasks, jobs in `infrastructure/scheduler/jobs/`, handles daily/hourly market data updates and real-time signal detection.

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

### Direct Registry Access Pattern
The system has been refactored to eliminate delegation patterns in favor of direct registry access:

**DO**: Use `strategy_registry` directly
```python
from domain.orchestration.strategy_registry import strategy_registry
config = strategy_registry.get_strategy_config(strategy_name, "static")
available = strategy_registry.get_available_strategies("dynamic")["dynamic"]
supported = strategy_registry.is_strategy_supported(strategy_identifier)
```

**DON'T**: Create wrapper/delegation functions - they have been systematically removed from the codebase.

### Strategy Development
- Follow the modular structure: `domain/strategies/single/strategy_name/`
- Each strategy folder contains: implementation, detectors/, configs/
- Constructor signature: `__init__(self, strategy_type: StrategyType, config)`
- Strategy-specific detectors with custom weights and thresholds
- Reference existing strategies like `conservative/` or `balanced/` for structure

### Strategy Mix Development  
- Use `domain.strategies.mixes.utils.get_strategy_mix_config()` directly
- Configuration via `StrategyMixConfig` with mode-specific logic
- Centrally managed through `STRATEGY_MIXES` registry

### Market Data Providers
- New market indicators require database schema updates (ENUM additions)
- Use bulk operations (`bulk_save_objects`) for data storage efficiency
- Market data backfiller handles historical data gaps with 2-year rolling window optimization

### Code Conventions
- Domain-driven design with clear separation of concerns
- Repository pattern for data access with bulk operations
- Factory pattern for strategy instantiation with dependency injection
- Centralized registries over delegation patterns
- Performance optimization through caching at multiple levels

## Common Issues and Troubleshooting

### Strategy Initialization Errors
If you encounter strategy initialization failures, check:

1. **Constructor Signature**: All strategy classes should accept `(strategy_type: StrategyType, config)` parameters
2. **Config Classes**: Strategy-specific config classes must have required fields (name, description, signal_threshold, risk_per_trade)
3. **detector_weights**: Config classes should implement detector_weights attribute or inherit properly
4. **StrategyType Enum**: Ensure all strategy types are defined in `static_strategies.py`

### Missing Strategy Types
When adding new strategies:
- Add enum value to `StrategyType` in `domain/signals/models/enums/strategy_type.py`
- Add mapping in `STRATEGY_CLASS_MAP` in `domain/orchestration/factory.py`
- Implement proper config class with detector_weights
- Follow constructor pattern: `__init__(self, strategy_type: StrategyType, config)`
- Create strategy package in appropriate location: `domain/strategies/single/strategy_name/`

### Database Schema Updates
When adding new market indicators:
- Update `MarketIndicatorType` enum in database models
- Run schema migration to add new ENUM values
- Update provider configs in `market_data_backfiller/config.py`