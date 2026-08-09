from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from paper_order_lifecycle.service import PaperOrderLifecycleMonitor
from paper_position_lifecycle.rules import evaluate_exit


class AlpacaPaperOrderPositionLifecycleBridgeV2123:
    """
    Read-only lifecycle bridge for a V2.1.22 submitted Alpaca Paper order.

    Reuses:
      - paper_order_lifecycle.PaperOrderLifecycleMonitor
      - paper_position_lifecycle.rules.evaluate_exit

    This stage never submits entry or exit orders.
    """

    def __init__(
        self,
        root,
        *,
        monitor_factory=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.execution_ledger=(
            self.root/"runtime"/"alpaca_paper_bounded_execution_v2_1_22"/
            "execution_ledger.jsonl"
        )
        self.policy_path=(
            self.root/"release"/"v95_33_to_v95_64"/"input"/
            "position_lifecycle_policy.json"
        )
        self.runtime_dir=(
            self.root/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)

        self.compat_result=self.runtime_dir/"v2_1_22_order_compat.json"
        self.monitor_dir=self.runtime_dir/"order_lifecycle"
        self.latest=self.runtime_dir/"latest_lifecycle.json"
        self.ledger=self.runtime_dir/"lifecycle_ledger.jsonl"

        self.monitor_factory=monitor_factory or (lambda:PaperOrderLifecycleMonitor())
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

    def _read_submission_rows(self):
        if not self.execution_ledger.exists():
            return []
        rows=[]
        for line in self.execution_ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            if row.get("paper_order_submitted") is True:
                rows.append(row)
        return rows

    def _latest_submission(self):
        rows=self._read_submission_rows()
        return rows[-1] if rows else None

    def _write(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,ensure_ascii=False,default=str),
            encoding="utf-8",
        )
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(row,sort_keys=True,ensure_ascii=False,default=str)+"\n"
            )
        return row

    @staticmethod
    def _position_for_exit_rule(snapshot):
        position=snapshot.get("position") or {}
        avg=position.get("avg_entry_price")
        qty=position.get("qty")
        current=position.get("current_price")
        return {
            "average_cost":float(avg or 0),
            "quantity":float(qty or 0),
            "mark_price":float(current or 0),
        }

    def build_dry_plan(self):
        submission=self._latest_submission()
        if submission is None:
            return self._write({
                "status":"WAITING_FOR_V2_1_22_PAPER_ORDER",
                "paper_order_submitted_from_stage":False,
                "exit_order_submitted":False,
                "live_order_submitted":False,
            })

        order=submission.get("order") or {}
        client_order_id=(
            submission.get("client_order_id")
            or order.get("client_order_id")
        )
        broker_order_id=order.get("id")
        if not client_order_id:
            return self._write({
                "status":"BLOCKED_CLIENT_ORDER_ID_MISSING",
                "exit_order_submitted":False,
                "live_order_submitted":False,
            })

        return self._write({
            "status":"READY_FOR_READ_ONLY_ORDER_LIFECYCLE_MONITOR",
            "evidence_key":submission.get("evidence_key"),
            "client_order_id":client_order_id,
            "broker_order_id":broker_order_id,
            "selected_candidate":submission.get("selected_candidate"),
            "paper_only":True,
            "broker_read_allowed":True,
            "broker_write_allowed":False,
            "entry_order_submitted_from_stage":False,
            "exit_order_submitted":False,
            "live_order_submitted":False,
        })

    def monitor_once(self, *, interval_seconds=1, max_cycles=12):
        plan=self.build_dry_plan()
        if plan.get("status")!="READY_FOR_READ_ONLY_ORDER_LIFECYCLE_MONITOR":
            return plan

        submission=self._latest_submission()
        order=submission.get("order") or {}

        compat={
            "broker_response":{
                "id":order.get("id"),
                "client_order_id":(
                    submission.get("client_order_id")
                    or order.get("client_order_id")
                ),
            },
            "reconciliation":{
                "client_order_id":(
                    submission.get("client_order_id")
                    or order.get("client_order_id")
                ),
            },
            "source_stage":"V2.1.22",
            "paper_only":True,
        }
        self.compat_result.write_text(
            json.dumps(compat,indent=2,sort_keys=True),
            encoding="utf-8",
        )

        monitor=self.monitor_factory()
        summary=monitor.monitor(
            p3_result_path=self.compat_result,
            output_dir=self.monitor_dir,
            interval_seconds=interval_seconds,
            max_cycles=max_cycles,
        )

        final_snapshot=summary.get("final_snapshot") or {}
        final_status=str(summary.get("final_status") or "")
        position_found=bool(final_snapshot.get("position_found"))
        decision=None
        lifecycle_state="ORDER_NOT_FILLED_OR_POSITION_NOT_FOUND"

        if final_status=="filled" and position_found:
            if not self.policy_path.exists():
                return self._write({
                    **plan,
                    "status":"BLOCKED_POSITION_LIFECYCLE_POLICY_MISSING",
                    "order_lifecycle_summary":summary,
                    "exit_order_submitted":False,
                    "live_order_submitted":False,
                })

            policy=json.loads(self.policy_path.read_text(encoding="utf-8"))
            data=self._position_for_exit_rule(final_snapshot)
            position={
                "average_cost":data["average_cost"],
                "quantity":data["quantity"],
            }
            mark=data["mark_price"]
            decision=evaluate_exit(
                position,
                mark,
                0,
                max(data["average_cost"],mark),
                policy,
            )
            lifecycle_state=(
                "POSITION_EXIT_READY_READ_ONLY"
                if decision.get("action")=="EXIT"
                else "POSITION_HOLD_READ_ONLY"
            )

        result={
            **plan,
            "status":(
                "PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY"
                if summary.get("status")=="PASS"
                else "BLOCKED_ORDER_LIFECYCLE_RECONCILIATION"
            ),
            "order_lifecycle_summary":summary,
            "position_lifecycle_state":lifecycle_state,
            "position_exit_decision":decision,
            "position_policy_path":str(self.policy_path),
            "broker_read_performed":bool(
                summary.get("actual_broker_read_performed")
            ),
            "broker_write_performed":False,
            "entry_order_submitted_from_stage":False,
            "exit_order_submitted":False,
            "live_order_submitted":False,
            "actual_paper_orders_submitted_from_stage":0,
            "actual_live_orders_submitted_from_stage":0,
            "observed_at_utc":self.now_fn().astimezone(timezone.utc).isoformat(),
        }
        return self._write(result)
