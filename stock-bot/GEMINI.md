# GEMINI Project Context: stock-bot

## Common Commands
- **Install dependencies:** `pip install -r requirements.txt`
- **Run tests:** `pytest`
- **Run the application:** `python main.py`
- **Run a backtest:** `python run_backtest.py --strategy [strategy_name]`

## Architecture
- **Configuration:** Global settings are in `common/config/settings.py`. Strategy-specific configs are in `strategy_configs/`.
- **Strategies:** New trading strategies are defined as modules within the `domain/strategies/` directory. Each strategy should be self-contained in its own folder.
- **Database:** All database interaction is handled by `infrastructure/db/db_manager.py`. Avoid direct DB access elsewhere.
- **Data Providers:** Data fetching logic from external sources (like Yahoo Finance) is located in `infrastructure/client/`.

## Workflow: Adding a New Strategy
1.  Create a new directory for the strategy under `domain/strategies/`.
2.  Implement the strategy logic in a Python file within the new directory.
3.  Add a corresponding configuration file in `strategy_configs/`.
4.  Document the strategy in a new `.md` file in `strategy_docs/`.
5.  Run a backtest using `run_backtest.py` to validate.
