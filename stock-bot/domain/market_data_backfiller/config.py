# domain/market_data_backfiller/config.py
from infrastructure.db.models.enums import MarketIndicatorType

# 백필 가능한 모든 지표와 해당 Provider 설정을 정의합니다.
# 이 딕셔너리에 새로운 지표를 추가하여 기능을 확장할 수 있습니다.
BACKFILL_PROVIDERS_CONFIG = {
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
    "FEAR_GREED_INDEX": {
        "provider": "FearGreedBackfillProvider",
        "indicator_type": MarketIndicatorType.FEAR_GREED_INDEX,
    },
    "PUT_CALL_RATIO": {
        "provider": "PutCallRatioBackfillProvider",
        "indicator_type": MarketIndicatorType.PUT_CALL_RATIO,
    },
    "SP500_INDEX": {
        "provider": "YahooBackfillProvider",
        "symbol": "^GSPC",
        "indicator_type": MarketIndicatorType.SP500_INDEX,
    },
    "DXY": {
        "provider": "YahooBackfillProvider",
        "symbol": "DX-Y.NYB",
        "indicator_type": MarketIndicatorType.DXY,
    },
    "GOLD_PRICE": {
        "provider": "YahooBackfillProvider",
        "symbol": "GC=F",
        "indicator_type": MarketIndicatorType.GOLD_PRICE,
    },
    "CRUDE_OIL_PRICE": {
        "provider": "YahooBackfillProvider",
        "symbol": "CL=F",
        "indicator_type": MarketIndicatorType.CRUDE_OIL_PRICE,
    },
    # 'BUFFETT_INDICATOR'는 여러 데이터를 조합해야 하므로 별도의 Provider가 필요하지만,
    # 여기서는 예시로 FRED 기반 Provider를 사용하도록 설정합니다.
    "BUFFETT_INDICATOR": {
        "provider": "FredBackfillProvider",
        "symbol": "NCBEILQ027S", # 시가총액 데이터. GDP는 Provider 내부에서 별도 조회.
        "indicator_type": MarketIndicatorType.BUFFETT_INDICATOR,
    },
}

# 사용자가 실제로 백필을 실행할 지표 목록입니다.
# 이 리스트를 수정하여 원하는 지표만 선택적으로 실행할 수 있습니다.
ENABLED_PROVIDERS = [
    "VIX",
    "US_10Y_TREASURY_YIELD",
    "FEAR_GREED_INDEX",
    "PUT_CALL_RATIO",
    "SP500_INDEX",
    "DXY",
]
