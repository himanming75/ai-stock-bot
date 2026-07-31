"""Safe Alpaca market-data foundation and historical-data client boundary.

V79.01-V79.10 does not submit orders. V79.06-V79.10 defaults to an
offline fixture transport and performs no HTTP call or credential use.
"""
from .foundation_v79_01_05 import (
    AlpacaInstallStatus,
    MarketDataSafetyConfig,
    BarRequest,
    MarketBar,
    OfflineAlpacaMarketDataAdapter,
    inspect_alpaca_installation,
    load_safety_config,
    build_foundation_certificate,
)
from .historical_v79_06_10 import (
    HistoricalClientConfig,
    HistoricalBarsQuery,
    HistoricalBarRecord,
    AlpacaRequestFactory,
    FixtureHistoricalTransport,
    HistoricalDataNormalizer,
    HistoricalDataCache,
    SafeHistoricalDataService,
    inspect_historical_installation,
    build_historical_certificate,
)

__all__ = [
    "AlpacaInstallStatus",
    "MarketDataSafetyConfig",
    "BarRequest",
    "MarketBar",
    "OfflineAlpacaMarketDataAdapter",
    "inspect_alpaca_installation",
    "load_safety_config",
    "build_foundation_certificate",
    "HistoricalClientConfig",
    "HistoricalBarsQuery",
    "HistoricalBarRecord",
    "AlpacaRequestFactory",
    "FixtureHistoricalTransport",
    "HistoricalDataNormalizer",
    "HistoricalDataCache",
    "SafeHistoricalDataService",
    "inspect_historical_installation",
    "build_historical_certificate",
]
