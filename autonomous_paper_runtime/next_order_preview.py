from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json


class NextOrderPreviewState(str, Enum):
    WAIT_CYCLE_TOKEN = "WAIT_CYCLE_TOKEN"
    READY_FOR_SUBMISSION_APPROVAL = "READY_FOR_SUBMISSION_APPROVAL"
    DUPLICATE_PREVIEW = "DUPLICATE_PREVIEW"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class PreviewIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrderSubmissionPreview:
    preview_id: str
    cycle_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    order_type: str
    time_in_force: str
    estimated_price: str
    estimated_notional: str
    created_at: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextOrderPreviewReport:
    state: NextOrderPreviewState
    preview_created: bool
    duplicate_preview: bool
    payload_valid: bool
    risk_ok: bool
    exposure_ok: bool
    final_approval_required: bool
    actual_submission_allowed: bool
    safe_mode_engaged: bool
    reason: str
    preview_id: str
    preview_path: str
    risk_snapshot_path: str
    exposure_snapshot_path: str
    approval_gate_path: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[PreviewIssue, ...]
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "preview_created": self.preview_created,
            "duplicate_preview": self.duplicate_preview,
            "payload_valid": self.payload_valid,
            "risk_ok": self.risk_ok,
            "exposure_ok": self.exposure_ok,
            "final_approval_required": self.final_approval_required,
            "actual_submission_allowed": self.actual_submission_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "reason": self.reason,
            "preview_id": self.preview_id,
            "preview_path": self.preview_path,
            "risk_snapshot_path": self.risk_snapshot_path,
            "exposure_snapshot_path": self.exposure_snapshot_path,
            "approval_gate_path": self.approval_gate_path,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class ControlledNextOrderExecutionPreview:
    def __init__(
        self,
        *,
        preview_path: Path,
        risk_snapshot_path: Path,
        exposure_snapshot_path: Path,
        approval_gate_path: Path,
    ) -> None:
        self.preview_path = preview_path
        self.risk_snapshot_path = risk_snapshot_path
        self.exposure_snapshot_path = exposure_snapshot_path
        self.approval_gate_path = approval_gate_path

    def build(
        self,
        *,
        cycle_result: Mapping[str, Any],
        cycle_token: Mapping[str, Any] | None,
        account_snapshot: Mapping[str, Any],
        risk_snapshot: Mapping[str, Any],
        exposure_snapshot: Mapping[str, Any],
        created_at: str,
        max_quantity: str = "1",
        max_notional: str = "100",
        network_requests_executed: int = 0,
    ) -> NextOrderPreviewReport:
        issues: list[PreviewIssue] = []

        state = _text(cycle_result.get("state", "")).upper()
        preview_ready = bool(cycle_result.get("preview_ready", False))
        next_order_allowed = bool(
            cycle_result.get("next_order_allowed", False)
        )
        safe_mode = bool(cycle_result.get("safe_mode_engaged", False))

        if safe_mode:
            return self._report(
                state=NextOrderPreviewState.SAFE_MODE,
                reason="upstream_cycle_safe_mode",
                safe_mode=True,
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        if state in {
            "WAIT_ACTIVE_ORDER",
            "WAIT_MARKET_CLOSED",
            "WAIT_RISK",
            "WAIT_ACCOUNT",
            "WAIT_EXPOSURE",
            "WAIT_TERMINAL_COMMIT",
        } or not preview_ready or not next_order_allowed:
            return self._report(
                state=NextOrderPreviewState.WAIT_CYCLE_TOKEN,
                reason="cycle_not_ready",
                safe_mode=False,
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        if not cycle_token:
            issues.append(PreviewIssue(
                code="MISSING_CYCLE_TOKEN",
                expected="cycle token present",
                actual="missing",
                blocking=True,
                detail="submission preview requires a persisted cycle token",
            ))
            return self._report(
                state=NextOrderPreviewState.SAFE_MODE,
                reason="missing_cycle_token",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        cycle_id = _text(cycle_token.get("cycle_id", ""))
        symbol = _text(cycle_token.get("symbol", "")).upper()
        side = _text(cycle_token.get("side", "")).upper()
        quantity = _decimal(cycle_token.get("quantity", "0"))
        estimated_price = _decimal(
            cycle_token.get("estimated_price", "0")
        )
        estimated_notional = _decimal(
            cycle_token.get(
                "estimated_notional",
                quantity * estimated_price,
            )
        )
        max_quantity_d = _decimal(max_quantity)
        max_notional_d = _decimal(max_notional)

        account_active = (
            _text(account_snapshot.get("status", "")).upper() == "ACTIVE"
        )
        trading_blocked = _bool(
            account_snapshot.get("trading_blocked", False)
        )
        risk_ok = bool(risk_snapshot.get("approved", False))
        exposure_ok = bool(exposure_snapshot.get("approved", False))

        if not cycle_id:
            issues.append(PreviewIssue(
                code="MISSING_CYCLE_ID",
                expected="non-empty cycle_id",
                actual="",
                blocking=True,
                detail="cycle token has no stable identity",
            ))
        if not symbol:
            issues.append(PreviewIssue(
                code="MISSING_SYMBOL",
                expected="non-empty symbol",
                actual="",
                blocking=True,
                detail="preview requires a symbol",
            ))
        if side not in {"BUY", "SELL"}:
            issues.append(PreviewIssue(
                code="INVALID_SIDE",
                expected="BUY or SELL",
                actual=side,
                blocking=True,
                detail="unsupported side",
            ))
        if quantity <= 0 or quantity > max_quantity_d:
            issues.append(PreviewIssue(
                code="QUANTITY_CAP",
                expected=f"0 < quantity <= {max_quantity_d}",
                actual=str(quantity),
                blocking=True,
                detail="quantity exceeds preview cap",
            ))
        if estimated_price <= 0:
            issues.append(PreviewIssue(
                code="INVALID_ESTIMATED_PRICE",
                expected="estimated_price > 0",
                actual=str(estimated_price),
                blocking=True,
                detail="estimated price must be positive",
            ))
        if estimated_notional > max_notional_d:
            issues.append(PreviewIssue(
                code="NOTIONAL_CAP",
                expected=f"estimated_notional <= {max_notional_d}",
                actual=str(estimated_notional),
                blocking=True,
                detail="estimated notional exceeds preview cap",
            ))
        if not account_active:
            issues.append(PreviewIssue(
                code="ACCOUNT_NOT_ACTIVE",
                expected="ACTIVE",
                actual=_text(account_snapshot.get("status", "")),
                blocking=True,
                detail="broker account is not active",
            ))
        if trading_blocked:
            issues.append(PreviewIssue(
                code="TRADING_BLOCKED",
                expected="false",
                actual="true",
                blocking=True,
                detail="broker account is trading blocked",
            ))
        if not risk_ok:
            issues.append(PreviewIssue(
                code="RISK_NOT_APPROVED",
                expected="approved=true",
                actual="false",
                blocking=True,
                detail="risk snapshot did not approve preview",
            ))
        if not exposure_ok:
            issues.append(PreviewIssue(
                code="EXPOSURE_NOT_APPROVED",
                expected="approved=true",
                actual="false",
                blocking=True,
                detail="exposure snapshot did not approve preview",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        if blocking:
            return self._report(
                state=NextOrderPreviewState.SAFE_MODE,
                reason="preview_validation_failed",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
                risk_ok=risk_ok,
                exposure_ok=exposure_ok,
            )

        preview_id = self._preview_id(
            cycle_id=cycle_id,
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            estimated_price=str(estimated_price),
        )
        client_order_id = "BOT-AUTO-PAPER-V137-" + preview_id[-20:]

        preview = OrderSubmissionPreview(
            preview_id=preview_id,
            cycle_id=cycle_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            order_type="market",
            time_in_force="day",
            estimated_price=str(estimated_price),
            estimated_notional=str(estimated_notional),
            created_at=created_at,
        )

        if self.preview_path.exists():
            existing = json.loads(
                self.preview_path.read_text(encoding="utf-8")
            )
            if existing.get("preview_id") == preview_id:
                return self._report(
                    state=NextOrderPreviewState.DUPLICATE_PREVIEW,
                    reason="preview_already_exists",
                    safe_mode=False,
                    issues=(),
                    network_requests_executed=network_requests_executed,
                    preview_id=preview_id,
                    duplicate=True,
                    payload_valid=True,
                    risk_ok=True,
                    exposure_ok=True,
                    approval_required=True,
                )

            issues.append(PreviewIssue(
                code="DIFFERENT_PREVIEW_EXISTS",
                expected="no preview or matching preview_id",
                actual=str(existing.get("preview_id", "")),
                blocking=True,
                detail="a different active submission preview already exists",
            ))
            return self._report(
                state=NextOrderPreviewState.SAFE_MODE,
                reason="different_preview_exists",
                safe_mode=True,
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
                risk_ok=True,
                exposure_ok=True,
            )

        payload = {
            **preview.to_json_dict(),
            "broker_payload": {
                "symbol": symbol,
                "side": side.lower(),
                "qty": str(quantity),
                "type": "market",
                "time_in_force": "day",
                "client_order_id": client_order_id,
            },
        }
        risk_payload = {
            **dict(risk_snapshot),
            "preview_id": preview_id,
            "approved": True,
        }
        exposure_payload = {
            **dict(exposure_snapshot),
            "preview_id": preview_id,
            "approved": True,
        }
        approval_payload = {
            "preview_id": preview_id,
            "cycle_id": cycle_id,
            "state": "AWAITING_FINAL_SUBMISSION_APPROVAL",
            "final_approval_required": True,
            "actual_submission_allowed": False,
            "broker_write_performed": False,
        }

        for path, data in (
            (self.preview_path, payload),
            (self.risk_snapshot_path, risk_payload),
            (self.exposure_snapshot_path, exposure_payload),
            (self.approval_gate_path, approval_payload),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        return self._report(
            state=NextOrderPreviewState.READY_FOR_SUBMISSION_APPROVAL,
            reason="preview_package_created",
            safe_mode=False,
            issues=(),
            network_requests_executed=network_requests_executed,
            preview_id=preview_id,
            preview_created=True,
            payload_valid=True,
            risk_ok=True,
            exposure_ok=True,
            approval_required=True,
        )

    def _report(
        self,
        *,
        state: NextOrderPreviewState,
        reason: str,
        safe_mode: bool,
        issues: tuple[PreviewIssue, ...],
        network_requests_executed: int,
        preview_id: str = "",
        preview_created: bool = False,
        duplicate: bool = False,
        payload_valid: bool = False,
        risk_ok: bool = False,
        exposure_ok: bool = False,
        approval_required: bool = False,
    ) -> NextOrderPreviewReport:
        return NextOrderPreviewReport(
            state=state,
            preview_created=preview_created,
            duplicate_preview=duplicate,
            payload_valid=payload_valid,
            risk_ok=risk_ok,
            exposure_ok=exposure_ok,
            final_approval_required=approval_required,
            actual_submission_allowed=False,
            safe_mode_engaged=safe_mode,
            reason=reason,
            preview_id=preview_id,
            preview_path=str(self.preview_path),
            risk_snapshot_path=str(self.risk_snapshot_path),
            exposure_snapshot_path=str(self.exposure_snapshot_path),
            approval_gate_path=str(self.approval_gate_path),
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
    def _preview_id(
        *,
        cycle_id: str,
        symbol: str,
        side: str,
        quantity: str,
        estimated_price: str,
    ) -> str:
        raw = "|".join([
            cycle_id,
            symbol,
            side,
            quantity,
            estimated_price,
        ])
        return "PREVIEW-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
