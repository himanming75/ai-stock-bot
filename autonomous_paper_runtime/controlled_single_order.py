from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence
import hashlib
import time


class ControlledOrderDecision(str, Enum):
    BLOCKED = "BLOCKED"
    PREVIEW_READY = "PREVIEW_READY"
    SUBMITTED = "SUBMITTED"
    EXISTING_ORDER_WAIT = "EXISTING_ORDER_WAIT"


@dataclass(frozen=True)
class ControlledSingleOrderPolicy:
    allowed_symbols: tuple[str, ...] = ("AAPL", "SPY", "QQQ")
    max_quantity: Decimal = Decimal("1")
    max_order_notional: Decimal = Decimal("100")
    require_market_open: bool = True
    require_zero_open_orders: bool = True
    required_readiness_state: str = "PAPER_WRITE_READY"
    client_order_prefix: str = "BOT-AUTO-PAPER-V127-"

    def validate(self) -> None:
        if not self.allowed_symbols:
            raise ValueError("allowed_symbols cannot be empty")
        if self.max_quantity <= 0:
            raise ValueError("max_quantity must be positive")
        if self.max_order_notional <= 0:
            raise ValueError("max_order_notional must be positive")
        if not self.client_order_prefix:
            raise ValueError("client_order_prefix is required")


@dataclass(frozen=True)
class ControlledSingleOrderRequest:
    symbol: str
    side: str
    quantity: Decimal
    estimated_price: Decimal
    order_type: str = "market"
    time_in_force: str = "day"

    @property
    def estimated_notional(self) -> Decimal:
        return self.quantity * self.estimated_price


@dataclass(frozen=True)
class ControlledSingleOrderResult:
    decision: ControlledOrderDecision
    reason: str
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    estimated_price: str
    estimated_notional: str
    broker_order_id: str
    broker_status: str
    existing_open_order_count: int
    readiness_verified: bool
    market_open_verified: bool
    account_verified: bool
    approval_verified: bool
    live_trading_enabled: bool
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["decision"] = self.decision.value
        return raw


class PaperBrokerProtocol(Protocol):
    network_requests_executed: int
    write_requests_executed: int

    def get_account(self) -> Any: ...
    def get_clock(self) -> Any: ...
    def list_orders(self, *, status: str = "open", limit: int = 50) -> Sequence[Any]: ...
    def preview_submit_order(self, payload: dict[str, object]) -> dict[str, object]: ...
    def submit_order(self, payload: dict[str, object]) -> Any: ...


class ControlledAutonomousPaperSingleOrder:
    APPROVAL_TEXT = "SUBMIT EXACTLY ONE CONTROLLED ALPACA PAPER ORDER"

    def __init__(
        self,
        *,
        policy: ControlledSingleOrderPolicy | None = None,
    ) -> None:
        self.policy = policy or ControlledSingleOrderPolicy()
        self.policy.validate()

    def execute(
        self,
        *,
        broker: PaperBrokerProtocol,
        request: ControlledSingleOrderRequest,
        readiness_result: Mapping[str, Any],
        submit_enabled: bool,
        approval_text: str,
        client_order_nonce: str,
    ) -> ControlledSingleOrderResult:
        symbol = request.symbol.upper().strip()
        side = request.side.lower().strip()
        client_order_id = self._client_order_id(
            symbol=symbol,
            side=side,
            nonce=client_order_nonce,
        )

        readiness_verified = (
            str(readiness_result.get("state", "")).upper()
            == self.policy.required_readiness_state
            and bool(readiness_result.get("paper_write_ready", False))
            and bool(readiness_result.get("approval_token_verified", False))
        )
        approval_verified = (
            submit_enabled and approval_text.strip() == self.APPROVAL_TEXT
        )

        if symbol not in self.policy.allowed_symbols:
            return self._blocked(
                request, client_order_id, "symbol_not_allowed",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if side not in {"buy", "sell"}:
            return self._blocked(
                request, client_order_id, "side_not_allowed",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if request.quantity <= 0 or request.quantity > self.policy.max_quantity:
            return self._blocked(
                request, client_order_id, "quantity_limit",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if request.estimated_price <= 0:
            return self._blocked(
                request, client_order_id, "invalid_estimated_price",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if request.estimated_notional > self.policy.max_order_notional:
            return self._blocked(
                request, client_order_id, "notional_limit",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if request.order_type.lower() != "market":
            return self._blocked(
                request, client_order_id, "only_market_order_allowed",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if request.time_in_force.lower() != "day":
            return self._blocked(
                request, client_order_id, "only_day_tif_allowed",
                readiness_verified, False, False, approval_verified, broker, 0
            )
        if not readiness_verified:
            return self._blocked(
                request, client_order_id, "paper_write_readiness_missing",
                readiness_verified, False, False, approval_verified, broker, 0
            )

        account = broker.get_account()
        account_verified = (
            str(getattr(account, "status", "")).upper() == "ACTIVE"
            and not bool(getattr(account, "trading_blocked", True))
        )
        if not account_verified:
            return self._blocked(
                request, client_order_id, "account_not_ready",
                readiness_verified, False, account_verified,
                approval_verified, broker, 0
            )

        clock = broker.get_clock()
        market_open_verified = bool(getattr(clock, "is_open", False))
        if self.policy.require_market_open and not market_open_verified:
            return self._blocked(
                request, client_order_id, "market_closed",
                readiness_verified, market_open_verified, account_verified,
                approval_verified, broker, 0
            )

        open_orders = tuple(broker.list_orders(status="open", limit=50))
        if self.policy.require_zero_open_orders and open_orders:
            return self._result(
                decision=ControlledOrderDecision.EXISTING_ORDER_WAIT,
                reason="existing_open_order_blocks_new_submission",
                request=request,
                client_order_id=client_order_id,
                broker_order_id="",
                broker_status="",
                existing_open_order_count=len(open_orders),
                readiness_verified=readiness_verified,
                market_open_verified=market_open_verified,
                account_verified=account_verified,
                approval_verified=approval_verified,
                broker=broker,
                paper_orders=0,
            )

        payload = {
            "symbol": symbol,
            "qty": str(request.quantity),
            "side": side,
            "type": "market",
            "time_in_force": "day",
            "client_order_id": client_order_id,
        }
        broker.preview_submit_order(payload)

        if not approval_verified:
            return self._result(
                decision=ControlledOrderDecision.PREVIEW_READY,
                reason="explicit_submission_approval_required",
                request=request,
                client_order_id=client_order_id,
                broker_order_id="",
                broker_status="",
                existing_open_order_count=0,
                readiness_verified=readiness_verified,
                market_open_verified=market_open_verified,
                account_verified=account_verified,
                approval_verified=approval_verified,
                broker=broker,
                paper_orders=0,
            )

        submitted = broker.submit_order(payload)
        return self._result(
            decision=ControlledOrderDecision.SUBMITTED,
            reason="exactly_one_paper_order_submitted",
            request=request,
            client_order_id=client_order_id,
            broker_order_id=str(
                getattr(submitted, "order_id", getattr(submitted, "id", ""))
            ),
            broker_status=str(getattr(submitted, "status", "")),
            existing_open_order_count=0,
            readiness_verified=readiness_verified,
            market_open_verified=market_open_verified,
            account_verified=account_verified,
            approval_verified=approval_verified,
            broker=broker,
            paper_orders=1,
        )

    def _blocked(
        self,
        request: ControlledSingleOrderRequest,
        client_order_id: str,
        reason: str,
        readiness_verified: bool,
        market_open_verified: bool,
        account_verified: bool,
        approval_verified: bool,
        broker: PaperBrokerProtocol,
        existing_open_orders: int,
    ) -> ControlledSingleOrderResult:
        return self._result(
            decision=ControlledOrderDecision.BLOCKED,
            reason=reason,
            request=request,
            client_order_id=client_order_id,
            broker_order_id="",
            broker_status="",
            existing_open_order_count=existing_open_orders,
            readiness_verified=readiness_verified,
            market_open_verified=market_open_verified,
            account_verified=account_verified,
            approval_verified=approval_verified,
            broker=broker,
            paper_orders=0,
        )

    @staticmethod
    def _result(
        *,
        decision: ControlledOrderDecision,
        reason: str,
        request: ControlledSingleOrderRequest,
        client_order_id: str,
        broker_order_id: str,
        broker_status: str,
        existing_open_order_count: int,
        readiness_verified: bool,
        market_open_verified: bool,
        account_verified: bool,
        approval_verified: bool,
        broker: PaperBrokerProtocol,
        paper_orders: int,
    ) -> ControlledSingleOrderResult:
        return ControlledSingleOrderResult(
            decision=decision,
            reason=reason,
            client_order_id=client_order_id,
            symbol=request.symbol.upper(),
            side=request.side.upper(),
            quantity=str(request.quantity),
            estimated_price=str(request.estimated_price),
            estimated_notional=str(request.estimated_notional),
            broker_order_id=broker_order_id,
            broker_status=broker_status,
            existing_open_order_count=existing_open_order_count,
            readiness_verified=readiness_verified,
            market_open_verified=market_open_verified,
            account_verified=account_verified,
            approval_verified=approval_verified,
            live_trading_enabled=False,
            network_requests_executed=int(
                getattr(broker, "network_requests_executed", 0)
            ),
            write_requests_executed=int(
                getattr(broker, "write_requests_executed", 0)
            ),
            actual_paper_orders_submitted=paper_orders,
            live_orders_submitted=0,
        )

    def _client_order_id(self, *, symbol: str, side: str, nonce: str) -> str:
        digest = hashlib.sha256(
            f"{symbol}|{side}|{nonce}".encode("utf-8")
        ).hexdigest()[:20]
        return f"{self.policy.client_order_prefix}{digest}"
