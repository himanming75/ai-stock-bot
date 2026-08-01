from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from urllib.parse import quote, urlencode

from .config import AlpacaPaperConfig
from .errors import AlpacaNetworkDisabledError, AlpacaResponseError
from .models import BrokerAccount, BrokerClock, BrokerOrder, BrokerPosition, BrokerResponse
from .transport import HttpTransport


def _decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise AlpacaResponseError(f"invalid decimal field: {field}") from exc


def _datetime(value: object, field: str) -> datetime:
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception as exc:
        raise AlpacaResponseError(f"invalid datetime field: {field}") from exc


class AlpacaPaperClient:
    def __init__(
        self,
        *,
        config: AlpacaPaperConfig,
        api_key: str,
        secret_key: str,
        transport: HttpTransport,
    ) -> None:
        config.validate()
        if not api_key or not secret_key:
            raise ValueError("credentials are required")
        self.config = config
        self.transport = transport
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Accept": "application/json",
            "User-Agent": config.user_agent,
        }
        self.network_requests_executed = 0
        self.write_requests_executed = 0

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        write: bool = False,
    ) -> BrokerResponse:
        if write:
            if not self.config.network_write_enabled:
                raise AlpacaNetworkDisabledError("Alpaca paper write network is disabled")
        elif not self.config.network_read_enabled:
            raise AlpacaNetworkDisabledError("Alpaca paper read network is disabled")

        url = self.config.base_url.rstrip("/") + path
        if query:
            url += "?" + urlencode({k: v for k, v in query.items() if v is not None})
        response = self.transport.request(
            method=method,
            url=url,
            headers=self._headers,
            timeout_seconds=self.config.timeout_seconds,
            body=body,
            max_retries=self.config.max_retries,
        )
        self.network_requests_executed += 1
        if write:
            self.write_requests_executed += 1
        return response

    def get_account(self) -> BrokerAccount:
        payload = self._request("GET", "/v2/account").payload
        if not isinstance(payload, dict):
            raise AlpacaResponseError("account response must be an object")
        return BrokerAccount(
            account_id=str(payload["id"]),
            status=str(payload["status"]),
            cash=_decimal(payload["cash"], "cash"),
            equity=_decimal(payload["equity"], "equity"),
            buying_power=_decimal(payload["buying_power"], "buying_power"),
            trading_blocked=bool(payload.get("trading_blocked", False)),
        )

    def get_clock(self) -> BrokerClock:
        payload = self._request("GET", "/v2/clock").payload
        if not isinstance(payload, dict):
            raise AlpacaResponseError("clock response must be an object")
        return BrokerClock(
            timestamp=_datetime(payload["timestamp"], "timestamp"),
            is_open=bool(payload["is_open"]),
            next_open=_datetime(payload["next_open"], "next_open"),
            next_close=_datetime(payload["next_close"], "next_close"),
        )

    def list_positions(self) -> tuple[BrokerPosition, ...]:
        payload = self._request("GET", "/v2/positions").payload
        if not isinstance(payload, list):
            raise AlpacaResponseError("positions response must be an array")
        return tuple(
            BrokerPosition(
                symbol=str(item["symbol"]).upper(),
                quantity=_decimal(item["qty"], "qty"),
                average_entry_price=_decimal(item["avg_entry_price"], "avg_entry_price"),
                market_value=_decimal(item["market_value"], "market_value"),
                unrealized_pnl=_decimal(item["unrealized_pl"], "unrealized_pl"),
            )
            for item in payload
        )

    def list_orders(self, *, status: str = "open", limit: int = 50) -> tuple[BrokerOrder, ...]:
        if status not in {"open", "closed", "all"}:
            raise ValueError("invalid order status filter")
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        payload = self._request(
            "GET", "/v2/orders", query={"status": status, "limit": limit}
        ).payload
        if not isinstance(payload, list):
            raise AlpacaResponseError("orders response must be an array")
        return tuple(self._parse_order(item) for item in payload)

    def get_order_by_client_id(self, client_order_id: str) -> BrokerOrder:
        payload = self._request(
            "GET",
            "/v2/orders:by_client_order_id",
            query={"client_order_id": client_order_id},
        ).payload
        return self._parse_order(payload)

    def preview_submit_order(self, payload: dict[str, object]) -> dict[str, object]:
        required = {"symbol", "qty", "side", "type", "time_in_force", "client_order_id"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"missing order payload fields: {', '.join(missing)}")
        return {
            "method": "POST",
            "url": self.config.base_url.rstrip("/") + "/v2/orders",
            "payload": dict(payload),
            "network_executed": False,
        }

    def submit_order(self, payload: dict[str, object]) -> BrokerOrder:
        response = self._request("POST", "/v2/orders", body=payload, write=True)
        return self._parse_order(response.payload)

    def cancel_order(self, order_id: str) -> BrokerResponse:
        safe_order_id = quote(order_id, safe="")
        return self._request("DELETE", f"/v2/orders/{safe_order_id}", write=True)

    @staticmethod
    def _parse_order(payload: object) -> BrokerOrder:
        if not isinstance(payload, dict):
            raise AlpacaResponseError("order response must be an object")
        return BrokerOrder(
            order_id=str(payload["id"]),
            client_order_id=str(payload["client_order_id"]),
            symbol=str(payload["symbol"]).upper(),
            side=str(payload["side"]).lower(),
            quantity=_decimal(payload["qty"], "qty"),
            filled_quantity=_decimal(payload.get("filled_qty", "0"), "filled_qty"),
            status=str(payload["status"]),
        )
