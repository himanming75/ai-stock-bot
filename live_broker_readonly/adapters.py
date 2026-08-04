from __future__ import annotations
from typing import Any
from live_broker_readonly.capabilities import get_capabilities

class ReadOnlyAdapter:
    def __init__(
        self,
        adapter_name: str,
        fixture: dict[str, Any],
    ) -> None:
        self.adapter_name=adapter_name
        self.fixture=fixture
        self.capabilities=get_capabilities(adapter_name)

    def health(self) -> dict[str, Any]:
        return {
            "adapter_name":self.adapter_name,
            "healthy":True,
            "read_only":True,
            "network_used":False,
            "credentials_used":False,
            "source":"LOCAL_FIXTURE",
        }

    def account(self) -> dict[str, Any]:
        return dict(self.fixture.get("account",{}))

    def positions(self) -> list[dict[str, Any]]:
        value=self.fixture.get("positions",[])
        return list(value) if isinstance(value,list) else []

    def orders(self) -> list[dict[str, Any]]:
        value=self.fixture.get("orders",[])
        return list(value) if isinstance(value,list) else []

    def submit_order(self, *_args, **_kwargs):
        raise PermissionError("READ_ONLY_BOUNDARY: submit_order blocked")

    def cancel_order(self, *_args, **_kwargs):
        raise PermissionError("READ_ONLY_BOUNDARY: cancel_order blocked")

    def replace_order(self, *_args, **_kwargs):
        raise PermissionError("READ_ONLY_BOUNDARY: replace_order blocked")

def build_adapter(
    adapter_name: str,
    fixture: dict[str, Any],
) -> ReadOnlyAdapter:
    return ReadOnlyAdapter(adapter_name,fixture)
