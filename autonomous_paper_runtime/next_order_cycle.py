from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json


class NextOrderCycleState(str, Enum):
    WAIT_ACTIVE_ORDER = "WAIT_ACTIVE_ORDER"
    WAIT_MARKET_CLOSED = "WAIT_MARKET_CLOSED"
    WAIT_RISK = "WAIT_RISK"
    WAIT_ACCOUNT = "WAIT_ACCOUNT"
    WAIT_EXPOSURE = "WAIT_EXPOSURE"
    WAIT_TERMINAL_COMMIT = "WAIT_TERMINAL_COMMIT"
    SAFE_MODE = "SAFE_MODE"
    READY_FOR_SINGLE_ORDER_PREVIEW = "READY_FOR_SINGLE_ORDER_PREVIEW"
    DUPLICATE_CYCLE = "DUPLICATE_CYCLE"


@dataclass(frozen=True)
class NextOrderCycleIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextOrderCycleToken:
    cycle_id: str
    readiness_fingerprint: str
    symbol: str
    side: str
    quantity: str
    estimated_price: str
    estimated_notional: str
    created_at: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextOrderCycleReport:
    state: NextOrderCycleState
    cycle_created: bool
    duplicate_cycle: bool
    preview_ready: bool
    next_order_allowed: bool
    safe_mode_engaged: bool
    reason: str
    cycle_id: str
    cycle_token_written: bool
    cycle_token_path: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[NextOrderCycleIssue, ...]
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "cycle_created": self.cycle_created,
            "duplicate_cycle": self.duplicate_cycle,
            "preview_ready": self.preview_ready,
            "next_order_allowed": self.next_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "reason": self.reason,
            "cycle_id": self.cycle_id,
            "cycle_token_written": self.cycle_token_written,
            "cycle_token_path": self.cycle_token_path,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class ControlledAutonomousNextOrderCycle:
    def __init__(self, *, cycle_token_path: Path) -> None:
        self.cycle_token_path = cycle_token_path

    def evaluate(
        self,
        *,
        readiness_result: Mapping[str, Any],
        symbol: str,
        side: str,
        quantity: str,
        estimated_price: str,
        created_at: str,
        max_quantity: str = "1",
        max_notional: str = "100",
        network_requests_executed: int = 0,
    ) -> NextOrderCycleReport:
        issues: list[NextOrderCycleIssue] = []

        readiness_state = _text(readiness_result.get("state", "")).upper()
        ready = bool(readiness_result.get("ready", False))
        next_order_allowed = bool(
            readiness_result.get("next_order_allowed", False)
        )
        safe_mode = bool(
            readiness_result.get("safe_mode_engaged", False)
        )

        if safe_mode:
            return self._report(
                state=NextOrderCycleState.SAFE_MODE,
                reason="upstream_safe_mode",
                safe_mode=True,
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        wait_mapping = {
            "BLOCKED_ACTIVE_ORDER": (
                NextOrderCycleState.WAIT_ACTIVE_ORDER,
                "active_order_present",
            ),
            "BLOCKED_MARKET_CLOSED": (
                NextOrderCycleState.WAIT_MARKET_CLOSED,
                "market_closed",
            ),
            "BLOCKED_RISK": (
                NextOrderCycleState.WAIT_RISK,
                "risk_not_approved",
            ),
            "BLOCKED_ACCOUNT": (
                NextOrderCycleState.WAIT_ACCOUNT,
                "account_not_ready",
            ),
            "BLOCKED_EXPOSURE": (
                NextOrderCycleState.WAIT_EXPOSURE,
                "exposure_limit",
            ),
            "BLOCKED_TERMINAL_NOT_COMMITTED": (
                NextOrderCycleState.WAIT_TERMINAL_COMMIT,
                "terminal_not_committed",
            ),
        }

        if readiness_state in wait_mapping:
            state, reason = wait_mapping[readiness_state]
            return self._report(
                state=state,
                reason=reason,
                safe_mode=False,
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        if readiness_state != "READY" or not ready or not next_order_allowed:
            issues.append(NextOrderCycleIssue(
                code="READINESS_INCONSISTENT",
                expected="state=READY, ready=true, next_order_allowed=true",
                actual=(
                    f"state={readiness_state}, ready={ready}, "
                    f"next_order_allowed={next_order_allowed}"
                ),
                blocking=True,
                detail="readiness result is internally inconsistent",
            ))
            return self._report(
                state=NextOrderCycleState.SAFE_MODE,
                reason="readiness_inconsistent",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        symbol = _text(symbol).upper()
        side = _text(side).upper()
        quantity_d = _decimal(quantity)
        price_d = _decimal(estimated_price)
        max_quantity_d = _decimal(max_quantity)
        max_notional_d = _decimal(max_notional)
        notional = quantity_d * price_d

        if not symbol:
            issues.append(NextOrderCycleIssue(
                code="MISSING_SYMBOL",
                expected="non-empty symbol",
                actual="",
                blocking=True,
                detail="next-order preview requires a symbol",
            ))
        if side not in {"BUY", "SELL"}:
            issues.append(NextOrderCycleIssue(
                code="INVALID_SIDE",
                expected="BUY or SELL",
                actual=side,
                blocking=True,
                detail="unsupported order side",
            ))
        if quantity_d <= 0 or quantity_d > max_quantity_d:
            issues.append(NextOrderCycleIssue(
                code="QUANTITY_CAP",
                expected=f"0 < quantity <= {max_quantity_d}",
                actual=str(quantity_d),
                blocking=True,
                detail="quantity exceeds controlled cycle cap",
            ))
        if price_d <= 0:
            issues.append(NextOrderCycleIssue(
                code="INVALID_ESTIMATED_PRICE",
                expected="estimated_price > 0",
                actual=str(price_d),
                blocking=True,
                detail="estimated price must be positive",
            ))
        if notional > max_notional_d:
            issues.append(NextOrderCycleIssue(
                code="NOTIONAL_CAP",
                expected=f"notional <= {max_notional_d}",
                actual=str(notional),
                blocking=True,
                detail="estimated notional exceeds controlled cap",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        if blocking:
            return self._report(
                state=NextOrderCycleState.SAFE_MODE,
                reason="preview_validation_failed",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        readiness_fingerprint = self._fingerprint(readiness_result)
        cycle_id = self._cycle_id(
            readiness_fingerprint=readiness_fingerprint,
            symbol=symbol,
            side=side,
            quantity=str(quantity_d),
            estimated_price=str(price_d),
        )

        if self.cycle_token_path.exists():
            existing = json.loads(
                self.cycle_token_path.read_text(encoding="utf-8")
            )
            if existing.get("cycle_id") == cycle_id:
                return self._report(
                    state=NextOrderCycleState.DUPLICATE_CYCLE,
                    reason="cycle_already_created",
                    safe_mode=False,
                    issues=(),
                    network_requests_executed=network_requests_executed,
                    duplicate=True,
                    cycle_id=cycle_id,
                    preview_ready=True,
                    allowed=True,
                )

            issues.append(NextOrderCycleIssue(
                code="DIFFERENT_ACTIVE_CYCLE_TOKEN",
                expected="no existing token or matching cycle_id",
                actual=str(existing.get("cycle_id", "")),
                blocking=True,
                detail="another next-order cycle token already exists",
            ))
            return self._report(
                state=NextOrderCycleState.SAFE_MODE,
                reason="different_cycle_token_exists",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        token = NextOrderCycleToken(
            cycle_id=cycle_id,
            readiness_fingerprint=readiness_fingerprint,
            symbol=symbol,
            side=side,
            quantity=str(quantity_d),
            estimated_price=str(price_d),
            estimated_notional=str(notional),
            created_at=created_at,
        )
        self.cycle_token_path.parent.mkdir(parents=True, exist_ok=True)
        self.cycle_token_path.write_text(
            json.dumps(token.to_json_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return self._report(
            state=NextOrderCycleState.READY_FOR_SINGLE_ORDER_PREVIEW,
            reason="all_gates_passed_cycle_token_created",
            safe_mode=False,
            issues=(),
            network_requests_executed=network_requests_executed,
            cycle_created=True,
            cycle_id=cycle_id,
            token_written=True,
            preview_ready=True,
            allowed=True,
        )

    def _report(
        self,
        *,
        state: NextOrderCycleState,
        reason: str,
        safe_mode: bool,
        issues: tuple[NextOrderCycleIssue, ...],
        network_requests_executed: int,
        cycle_created: bool = False,
        duplicate: bool = False,
        cycle_id: str = "",
        token_written: bool = False,
        preview_ready: bool = False,
        allowed: bool = False,
    ) -> NextOrderCycleReport:
        return NextOrderCycleReport(
            state=state,
            cycle_created=cycle_created,
            duplicate_cycle=duplicate,
            preview_ready=preview_ready,
            next_order_allowed=allowed,
            safe_mode_engaged=safe_mode,
            reason=reason,
            cycle_id=cycle_id,
            cycle_token_written=token_written,
            cycle_token_path=str(self.cycle_token_path),
            issue_count=len(issues),
            blocking_issue_count=sum(
                1 for item in issues if item.blocking
            ),
            issues=issues,
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @staticmethod
    def _fingerprint(readiness_result: Mapping[str, Any]) -> str:
        raw = json.dumps(
            dict(readiness_result),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _cycle_id(
        *,
        readiness_fingerprint: str,
        symbol: str,
        side: str,
        quantity: str,
        estimated_price: str,
    ) -> str:
        raw = "|".join([
            readiness_fingerprint,
            symbol,
            side,
            quantity,
            estimated_price,
        ])
        return "NEXT-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()


def _decimal(value: Any):
    from decimal import Decimal
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))
