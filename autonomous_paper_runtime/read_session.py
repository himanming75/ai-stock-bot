from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True)
class AutonomousPaperReadSnapshot:
    generated_at: datetime
    account_id_redacted: str
    account_status: str
    trading_blocked: bool
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    market_is_open: bool
    clock_timestamp: datetime
    next_open: datetime | None
    next_close: datetime | None
    position_count: int
    open_order_count: int
    closed_order_count: int
    symbols_held: tuple[str, ...]
    read_request_count: int
    write_request_count: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int
    request_methods: tuple[str, ...]
    paper_base_url: str
    autonomous_read_ready: bool

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = str(value)
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
            elif isinstance(value, tuple):
                raw[key] = list(value)
        return raw


class AutonomousPaperReadSession:
    """GET-only account snapshot for the autonomous Paper runtime."""

    def __init__(self, *, client: Any, closed_order_limit: int = 50) -> None:
        if closed_order_limit < 1 or closed_order_limit > 500:
            raise ValueError("closed_order_limit must be between 1 and 500")

        config = getattr(client, "config", None)
        if config is None:
            raise ValueError("client config is required")
        if getattr(config, "base_url", "") != "https://paper-api.alpaca.markets":
            raise ValueError("only Alpaca Paper base URL is allowed")
        if not bool(getattr(config, "network_read_enabled", False)):
            raise ValueError("read network must be enabled")
        if bool(getattr(config, "network_write_enabled", False)):
            raise ValueError("write network must remain disabled")

        self.client = client
        self.closed_order_limit = closed_order_limit

    def run(self) -> AutonomousPaperReadSnapshot:
        account = self.client.get_account()
        clock = self.client.get_clock()
        positions = tuple(self.client.list_positions())
        open_orders = tuple(self.client.list_orders(status="open"))
        closed_orders = tuple(
            self.client.list_orders(
                status="closed",
                limit=self.closed_order_limit,
            )
        )

        request_methods = tuple(
            str(item).upper()
            for item in getattr(self.client, "request_methods", ("GET",) * 5)
        )
        if request_methods != ("GET", "GET", "GET", "GET", "GET"):
            raise RuntimeError("autonomous read session must use exactly five GET requests")

        write_count = int(getattr(self.client, "write_requests_executed", 0))
        if write_count != 0:
            raise RuntimeError("write requests detected during read session")

        account_id = str(
            getattr(account, "account_id", None)
            or getattr(account, "id", "")
        )
        symbols = tuple(
            sorted(
                str(getattr(position, "symbol", "")).upper()
                for position in positions
                if str(getattr(position, "symbol", "")).strip()
            )
        )

        trading_blocked = bool(
            getattr(account, "trading_blocked", False)
            or getattr(account, "account_blocked", False)
        )
        status = str(getattr(account, "status", "UNKNOWN")).upper()
        market_open = bool(
            getattr(clock, "is_open", None)
            if getattr(clock, "is_open", None) is not None
            else getattr(clock, "market_is_open", False)
        )

        snapshot = AutonomousPaperReadSnapshot(
            generated_at=datetime.now(timezone.utc),
            account_id_redacted=_redact_account_id(account_id),
            account_status=status,
            trading_blocked=trading_blocked,
            cash=_decimal_attr(account, "cash"),
            buying_power=_decimal_attr(account, "buying_power"),
            equity=_decimal_attr(account, "equity"),
            market_is_open=market_open,
            clock_timestamp=_datetime_attr(clock, "timestamp"),
            next_open=_optional_datetime_attr(clock, "next_open"),
            next_close=_optional_datetime_attr(clock, "next_close"),
            position_count=len(positions),
            open_order_count=len(open_orders),
            closed_order_count=len(closed_orders),
            symbols_held=symbols,
            read_request_count=int(
                getattr(self.client, "network_requests_executed", len(request_methods))
            ),
            write_request_count=write_count,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
            request_methods=request_methods,
            paper_base_url=str(self.client.config.base_url),
            autonomous_read_ready=(
                status in {"ACTIVE", "APPROVED", "PAPER_ONLY"}
                and not trading_blocked
            ),
        )
        return snapshot


def _decimal_attr(obj: Any, name: str) -> Decimal:
    value = getattr(obj, name, "0")
    return Decimal(str(value))


def _datetime_attr(obj: Any, name: str) -> datetime:
    value = getattr(obj, name)
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _optional_datetime_attr(obj: Any, name: str) -> datetime | None:
    value = getattr(obj, name, None)
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _redact_account_id(value: str) -> str:
    if not value:
        return "missing"
    if len(value) <= 6:
        return "*" * len(value)
    return value[:2] + ("*" * (len(value) - 4)) + value[-2:]
