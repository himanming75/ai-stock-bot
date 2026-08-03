from __future__ import annotations
from typing import Any
from paper_broker_adapter.base import BrokerAdapter
from paper_broker_adapter.mock import MockPaperBrokerAdapter
from paper_broker_adapter.alpaca_readonly import AlpacaReadOnlyAdapter
from paper_broker_adapter.ibkr_readonly import IBKRReadOnlyAdapter

def create_adapter(
    adapter_name: str,
    *,
    account: dict[str, Any] | None = None,
    positions: list[dict[str, Any]] | None = None,
) -> BrokerAdapter:
    normalized = adapter_name.strip().upper()
    if normalized in {"MOCK", "MOCK_PAPER"}:
        return MockPaperBrokerAdapter(account=account, positions=positions)
    if normalized in {"ALPACA", "ALPACA_READ_ONLY"}:
        return AlpacaReadOnlyAdapter(network_enabled=False)
    if normalized in {"IBKR", "IBKR_READ_ONLY"}:
        return IBKRReadOnlyAdapter(network_enabled=False)
    raise ValueError(f"Unsupported broker adapter: {adapter_name}")
