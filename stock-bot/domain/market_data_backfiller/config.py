# domain/market_data_backfiller/config.py
from infrastructure.db.models.enums import MarketIndicatorType

# 백필 가능한 모든 지표와 해당 Provider 설정을 정의합니다.
# 그룹으로 묶인 지표들은 하나의 Provider가 처리합니다.
BACKFILL_PROVIDERS_CONFIG = {
    # --- 개별 Provider ---
    "VIX": {
        "provider": "FredBackfillProvider",
        "symbol": "VIXCLS",
        "indicator_type": MarketIndicatorType.VIX,
    },
    "US_10Y_TREASURY_YIELD": {
        "provider": "FredBackfillProvider",
        "symbol": "DGS10",
        "indicator_type": MarketIndicatorType.US_10Y_TREASURY_YIELD,
    },
    "PUT_CALL_RATIO": {
        "provider": "PutCallRatioBackfillProvider",
    },
    "SP500_INDEX": {
        "provider": "YahooBackfillProvider",
        "symbol": "^GSPC",
        "indicator_type": MarketIndicatorType.SP500_INDEX,
    },
    # --- FEAR_GREED_GROUP ---
    "FEAR_GREED_INDEX":               {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_JUNK_BOND_DEMAND":    {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_MARKET_MOMENTUM":     {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_MARKET_VOLATILITY":   {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_PUT_CALL_OPTIONS":    {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_SAFE_HAVEN_DEMAND":   {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_STOCK_PRICE_BREADTH": {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
    "FEAR_GREED_STOCK_PRICE_STRENGTH":  {"provider": "FearGreedBackfillProvider", "group": "FEAR_GREED_GROUP"},
}

# 사용자가 실제로 백필을 실행할 지표 목록입니다.
ENABLED_PROVIDERS = [
    "VIX",
    "US_10Y_TREASURY_YIELD",
    "FEAR_GREED_INDEX", # 그룹에 속한 어떤 지표를 지정해도 전체 그룹이 실행됩니다.
    "PUT_CALL_RATIO",
    "SP500_INDEX",
]
