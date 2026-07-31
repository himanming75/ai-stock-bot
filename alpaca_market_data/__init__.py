"""Safe Alpaca market-data modules through V79.15."""
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
]
