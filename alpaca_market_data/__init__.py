"""Safe Alpaca market-data modules through V79.20."""
from .foundation_v79_01_05 import (
    AlpacaInstallStatus, MarketDataSafetyConfig, BarRequest, MarketBar,
    OfflineAlpacaMarketDataAdapter, inspect_alpaca_installation,
    load_safety_config, build_foundation_certificate,
)
from .historical_v79_06_10 import (
    HistoricalClientConfig, HistoricalBarsQuery, HistoricalBarRecord,
    AlpacaRequestFactory, FixtureHistoricalTransport,
    HistoricalDataNormalizer, HistoricalDataCache,
    SafeHistoricalDataService, inspect_historical_installation,
    build_historical_certificate,
)
from .authenticated_gate_v79_11_15 import (
    CredentialInspection, NetworkApproval, AuthenticatedClientPolicy,
    inspect_credentials, issue_network_approval, build_authenticated_client,
    authorize_historical_request, build_authenticated_gate_certificate,
)
from .network_smoke_v79_16_20 import (
    NetworkSmokeConfig, NetworkSmokePreflight, NetworkSmokeResult,
    inspect_network_smoke_preflight, build_bounded_stock_bars_request,
    execute_historical_network_smoke, sanitize_smoke_result,
    build_network_smoke_certificate,
)

__all__ = [
    "AlpacaInstallStatus", "MarketDataSafetyConfig", "BarRequest", "MarketBar",
    "OfflineAlpacaMarketDataAdapter", "inspect_alpaca_installation",
    "load_safety_config", "build_foundation_certificate",
    "HistoricalClientConfig", "HistoricalBarsQuery", "HistoricalBarRecord",
    "AlpacaRequestFactory", "FixtureHistoricalTransport",
    "HistoricalDataNormalizer", "HistoricalDataCache",
    "SafeHistoricalDataService", "inspect_historical_installation",
    "build_historical_certificate",
    "CredentialInspection", "NetworkApproval", "AuthenticatedClientPolicy",
    "inspect_credentials", "issue_network_approval", "build_authenticated_client",
    "authorize_historical_request", "build_authenticated_gate_certificate",
    "NetworkSmokeConfig", "NetworkSmokePreflight", "NetworkSmokeResult",
    "inspect_network_smoke_preflight", "build_bounded_stock_bars_request",
    "execute_historical_network_smoke", "sanitize_smoke_result",
    "build_network_smoke_certificate",
]
