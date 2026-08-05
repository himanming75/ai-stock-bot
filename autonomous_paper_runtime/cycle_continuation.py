from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from .next_order_readiness import AutonomousNextOrderReadinessGate
from .next_order_cycle import ControlledAutonomousNextOrderCycle
from .next_order_preview import ControlledNextOrderExecutionPreview
from .final_submission_approval import FinalPaperSubmissionApprovalGate


@dataclass(frozen=True)
class CycleContinuationReport:
    readiness_result: dict[str, Any]
    cycle_result: dict[str, Any]
    preview_result: dict[str, Any]
    approval_result: dict[str, Any]
    final_state: str
    stopped_at: str
    next_order_allowed: bool
    actual_submission_allowed: bool
    safe_mode_engaged: bool
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "readiness_result": self.readiness_result,
            "cycle_result": self.cycle_result,
            "preview_result": self.preview_result,
            "approval_result": self.approval_result,
            "final_state": self.final_state,
            "stopped_at": self.stopped_at,
            "next_order_allowed": self.next_order_allowed,
            "actual_submission_allowed": self.actual_submission_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class AutonomousCycleContinuationOrchestrator:
    def __init__(self, *, root: Path) -> None:
        self.root = root

    def run(
        self,
        *,
        terminal_monitor_result: Mapping[str, Any],
        account: Mapping[str, Any],
        open_orders: Sequence[Mapping[str, Any]],
        positions: Sequence[Mapping[str, Any]],
        market_is_open: bool,
        risk_approved: bool,
        symbol: str,
        side: str,
        quantity: str,
        estimated_price: str,
        max_positions: int = 3,
        max_total_market_value: str = "1000",
        max_quantity: str = "1",
        max_notional: str = "100",
        approval_phrase: str = "",
        created_at: str = "",
        network_requests_executed: int = 0,
    ) -> CycleContinuationReport:
        readiness_gate = AutonomousNextOrderReadinessGate(
            readiness_snapshot_path=self.root / "readiness.json"
        )
        readiness = readiness_gate.evaluate(
            terminal_monitor_result=terminal_monitor_result,
            account=account,
            open_orders=open_orders,
            positions=positions,
            market_is_open=market_is_open,
            risk_approved=risk_approved,
            max_positions=max_positions,
            max_total_market_value=Decimal(max_total_market_value),
            network_requests_executed=network_requests_executed,
        )
        readiness_dict = readiness.to_json_dict()

        cycle_gate = ControlledAutonomousNextOrderCycle(
            cycle_token_path=self.root / "next_order_cycle_token.json"
        )
        cycle = cycle_gate.evaluate(
            readiness_result=readiness_dict,
            symbol=symbol,
            side=side,
            quantity=quantity,
            estimated_price=estimated_price,
            created_at=created_at,
            max_quantity=max_quantity,
            max_notional=max_notional,
            network_requests_executed=network_requests_executed,
        )
        cycle_dict = cycle.to_json_dict()

        if not cycle.preview_ready:
            return self._stop(
                readiness=readiness_dict,
                cycle=cycle_dict,
                preview={},
                approval={},
                final_state=cycle.state.value,
                stopped_at="CYCLE_GATE",
                next_order_allowed=False,
                actual_submission_allowed=False,
                safe_mode=readiness.safe_mode_engaged or cycle.safe_mode_engaged,
                network_requests_executed=network_requests_executed,
            )

        token_path = self.root / "next_order_cycle_token.json"
        token = __import__("json").loads(token_path.read_text(encoding="utf-8"))

        preview_gate = ControlledNextOrderExecutionPreview(
            preview_path=self.root / "order_preview.json",
            risk_snapshot_path=self.root / "risk_snapshot.json",
            exposure_snapshot_path=self.root / "exposure_snapshot.json",
            approval_gate_path=self.root / "preview_approval_gate.json",
        )
        preview = preview_gate.build(
            cycle_result=cycle_dict,
            cycle_token=token,
            account_snapshot=account,
            risk_snapshot={"approved": risk_approved},
            exposure_snapshot={
                "approved": readiness.state.value == "READY",
                "position_count": readiness.position_count,
                "total_market_value": readiness.total_market_value,
            },
            created_at=created_at,
            max_quantity=max_quantity,
            max_notional=max_notional,
            network_requests_executed=network_requests_executed,
        )
        preview_dict = preview.to_json_dict()

        if preview.state.value not in {
            "READY_FOR_SUBMISSION_APPROVAL",
            "DUPLICATE_PREVIEW",
        }:
            return self._stop(
                readiness=readiness_dict,
                cycle=cycle_dict,
                preview=preview_dict,
                approval={},
                final_state=preview.state.value,
                stopped_at="PREVIEW_GATE",
                next_order_allowed=True,
                actual_submission_allowed=False,
                safe_mode=preview.safe_mode_engaged,
                network_requests_executed=network_requests_executed,
            )

        import json
        order_preview = json.loads(
            (self.root / "order_preview.json").read_text(encoding="utf-8")
        )
        risk_snapshot = json.loads(
            (self.root / "risk_snapshot.json").read_text(encoding="utf-8")
        )
        exposure_snapshot = json.loads(
            (self.root / "exposure_snapshot.json").read_text(encoding="utf-8")
        )
        preview_approval_gate = json.loads(
            (self.root / "preview_approval_gate.json").read_text(encoding="utf-8")
        )

        approval_gate = FinalPaperSubmissionApprovalGate(
            approval_token_path=self.root / "final_submission_approval_token.json",
            approval_audit_path=self.root / "final_submission_approval_audit.json",
        )
        approval = approval_gate.evaluate(
            preview_result=preview_dict,
            order_preview=order_preview,
            risk_snapshot=risk_snapshot,
            exposure_snapshot=exposure_snapshot,
            approval_gate=preview_approval_gate,
            approval_phrase=approval_phrase,
            approved_at=created_at,
            network_requests_executed=network_requests_executed,
        )
        approval_dict = approval.to_json_dict()

        return self._stop(
            readiness=readiness_dict,
            cycle=cycle_dict,
            preview=preview_dict,
            approval=approval_dict,
            final_state=approval.state.value,
            stopped_at="FINAL_APPROVAL_GATE",
            next_order_allowed=readiness.next_order_allowed,
            actual_submission_allowed=approval.actual_submission_allowed,
            safe_mode=approval.safe_mode_engaged,
            network_requests_executed=network_requests_executed,
        )

    @staticmethod
    def _stop(
        *,
        readiness: dict[str, Any],
        cycle: dict[str, Any],
        preview: dict[str, Any],
        approval: dict[str, Any],
        final_state: str,
        stopped_at: str,
        next_order_allowed: bool,
        actual_submission_allowed: bool,
        safe_mode: bool,
        network_requests_executed: int,
    ) -> CycleContinuationReport:
        return CycleContinuationReport(
            readiness_result=readiness,
            cycle_result=cycle,
            preview_result=preview,
            approval_result=approval,
            final_state=final_state,
            stopped_at=stopped_at,
            next_order_allowed=next_order_allowed,
            actual_submission_allowed=actual_submission_allowed,
            safe_mode_engaged=safe_mode,
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )
