from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from paper_autonomous_execution.service import PaperAutonomousExecutionService


EXIT_CONFIRMATION="CLOSE_ALPACA_PAPER_POSITION_ONCE"


class AlpacaPaperExitExecutionRecoveryGuardV2125:
    """
    One-time Alpaca Paper position close guarded by the current V2.1.23
    EXIT_READY decision and durable recovery state.

    Reuses the existing Paper service/preflight and its paper=True adapter/client.
    The actual close operation is Alpaca TradingClient.close_position(symbol).

    No live client is created.
    """

    def __init__(
        self,
        root,
        *,
        service_factory=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.lifecycle_latest=(
            self.root/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"/
            "latest_lifecycle.json"
        )
        self.profile_path=(
            self.root/"release"/"v14001_15000_paper_autonomous_execution"/
            "config"/"paper_execution_profile.json"
        )
        self.output_dir=(
            self.root/"release"/"v14001_15000_paper_autonomous_execution"
        )
        self.runtime_dir=(
            self.root/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.ledger=self.runtime_dir/"exit_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_exit_state.json"

        self.service_factory=service_factory or self._default_service
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

    def _default_service(self):
        return PaperAutonomousExecutionService(
            project_root=self.root,
            profile_path=self.profile_path,
            output_dir=self.output_dir,
        )

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_latest(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,ensure_ascii=False,default=str),
            encoding="utf-8",
        )
        return row

    def _append(self,row):
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(row,sort_keys=True,ensure_ascii=False,default=str)+"\n"
            )

    def _exit_rows(self):
        if not self.ledger.exists():
            return []
        out=[]
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def _submitted_fingerprints(self):
        return {
            str(r.get("exit_fingerprint_sha256"))
            for r in self._exit_rows()
            if r.get("paper_exit_order_submitted") is True
        }

    def build_plan(self):
        if not self.lifecycle_latest.exists():
            return self._write_latest({
                "status":"WAITING_FOR_V2_1_23_LIFECYCLE",
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
            })

        life=self._read_json(self.lifecycle_latest)
        state=str(life.get("position_lifecycle_state") or "")
        decision=life.get("position_exit_decision") or {}

        if (
            life.get("status")!="PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY"
            or state!="POSITION_EXIT_READY_READ_ONLY"
            or decision.get("action")!="EXIT"
        ):
            return self._write_latest({
                "status":"NO_ACTION_POSITION_NOT_EXIT_READY",
                "lifecycle_status":life.get("status"),
                "position_lifecycle_state":state,
                "position_exit_decision":decision or None,
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
            })

        candidate=life.get("selected_candidate") or {}
        symbol=str(candidate.get("symbol") or "").upper().strip()
        evidence_key=str(life.get("evidence_key") or "").strip()

        final_snapshot=(
            (life.get("order_lifecycle_summary") or {}).get("final_snapshot")
            or {}
        )
        position=final_snapshot.get("position") or {}
        position_symbol=str(
            position.get("symbol") or symbol
        ).upper().strip()

        if not symbol or not evidence_key:
            return self._write_latest({
                "status":"BLOCKED_EXIT_BINDING_MISSING",
                "symbol":symbol or None,
                "evidence_key":evidence_key or None,
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
            })

        if position_symbol and position_symbol!=symbol:
            return self._write_latest({
                "status":"BLOCKED_POSITION_SYMBOL_MISMATCH",
                "symbol":symbol,
                "position_symbol":position_symbol,
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
            })

        payload={
            "evidence_key":evidence_key,
            "symbol":symbol,
            "entry_client_order_id":life.get("client_order_id"),
            "exit_reason":decision.get("reason"),
            "position_qty":position.get("qty"),
            "position_avg_entry_price":position.get("avg_entry_price"),
        }
        fingerprint=hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",",":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()

        if fingerprint in self._submitted_fingerprints():
            return self._write_latest({
                "status":"BLOCKED_EXIT_ALREADY_SUBMITTED",
                **payload,
                "exit_fingerprint_sha256":fingerprint,
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
            })

        return self._write_latest({
            "status":"READY_FOR_ONE_TIME_ALPACA_PAPER_EXIT",
            **payload,
            "exit_fingerprint_sha256":fingerprint,
            "paper_only":True,
            "existing_paper_service_preflight_required":True,
            "open_position_recovery_check_required":True,
            "paper_exit_order_submitted":False,
            "live_order_submitted":False,
        })

    @staticmethod
    def _order_to_dict(order,symbol):
        return {
            "id":str(getattr(order,"id","")),
            "client_order_id":str(getattr(order,"client_order_id","")),
            "symbol":str(getattr(order,"symbol",symbol)),
            "side":str(getattr(order,"side","")),
            "status":str(getattr(order,"status","")),
            "paper":True,
        }

    def execute_once(self,confirmation):
        plan=self.build_plan()
        if plan.get("status")!="READY_FOR_ONE_TIME_ALPACA_PAPER_EXIT":
            return plan

        if confirmation!=EXIT_CONFIRMATION:
            return self._write_latest({
                **plan,
                "status":"BLOCKED_EXPLICIT_EXIT_CONFIRMATION_REQUIRED",
                "required_confirmation":EXIT_CONFIRMATION,
            })

        service=self.service_factory()
        preflight=service.preflight()
        if preflight.get("status")!="PASS":
            result={
                **plan,
                "status":"BLOCKED_PAPER_PREFLIGHT",
                "preflight":preflight,
            }
            self._append(result)
            return self._write_latest(result)

        symbol=plan["symbol"]
        open_symbols=service.adapter.open_position_symbols()

        if symbol not in open_symbols:
            result={
                **plan,
                "status":"RECOVERED_POSITION_ALREADY_CLOSED_NO_DUPLICATE_EXIT",
                "preflight":preflight,
                "open_position_symbols":sorted(open_symbols),
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
                "recovery_guard_triggered":True,
            }
            self._append(result)
            return self._write_latest(result)

        client=service.adapter._client()
        order=client.close_position(symbol)

        result={
            **plan,
            "status":"PAPER_EXIT_ORDER_SUBMITTED_ONCE",
            "preflight":preflight,
            "exit_order":self._order_to_dict(order,symbol),
            "submitted_at_utc":
                self.now_fn().astimezone(timezone.utc).isoformat(),
            "paper_exit_order_submitted":True,
            "live_order_submitted":False,
            "recovery_guard_triggered":False,
        }
        self._append(result)
        return self._write_latest(result)

    def recover_state(self):
        """
        Read-only local recovery summary. No broker client is created.
        """
        rows=self._exit_rows()
        submitted=[
            r for r in rows
            if r.get("paper_exit_order_submitted") is True
        ]
        recovered=[
            r for r in rows
            if r.get("recovery_guard_triggered") is True
        ]
        return self._write_latest({
            "status":"PASS_LOCAL_RESTART_RECOVERY_STATE",
            "exit_ledger_rows":len(rows),
            "submitted_exit_rows":len(submitted),
            "recovery_guard_rows":len(recovered),
            "submitted_fingerprints":sorted(
                self._submitted_fingerprints()
            ),
            "broker_network_used":False,
            "paper_exit_order_submitted":False,
            "live_order_submitted":False,
        })
