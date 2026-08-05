from __future__ import annotations
from typing import Any, Callable


class LiveReadMethodError(RuntimeError):
    pass


class LiveReadNetworkBlocked(RuntimeError):
    pass


class GetOnlyHttpGuard:
    def __init__(
        self,
        *,
        network_enabled: bool,
        transport: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.network_enabled = network_enabled
        self.transport = transport

    def request_json(self, method: str, path: str) -> Any:
        normalized = method.strip().upper()
        if normalized != "GET":
            raise LiveReadMethodError(
                f"LIVE_READ_ONLY_METHOD_REJECTED:{normalized}"
            )
        if not self.network_enabled:
            if self.transport is None:
                raise LiveReadNetworkBlocked(
                    "LIVE_READ_NETWORK_DISABLED"
                )
            return self.transport(normalized, path)
        if self.transport is None:
            raise RuntimeError("LIVE_READ_TRANSPORT_NOT_CONFIGURED")
        return self.transport(normalized, path)
