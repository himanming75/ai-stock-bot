from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from paper_autonomous_execution.config import PaperExecutionProfile
from paper_autonomous_execution.service import PaperAutonomousExecutionService
from paper_autonomous_execution.signals import load_signal_candidates, select_candidate


CONFIRMATION_PHRASE="SUBMIT_ALPACA_PAPER_ONCE"


class AlpacaPaperBoundedExecutionBridgeV2122:
    """
    Bounded handoff from the CURRENT V2.1.21 READY evidence to the repository's
    existing Alpaca Paper execution adapter.

    This class creates no broker client and no order request itself.
    It reuses:
      - PaperExecutionProfile
      - PaperAutonomousExecutionService.preflight()
      - service.adapter.open_position_symbols()
      - service.adapter.submit_market_notional()
      - canonical select_candidate()

    Installation/tests never call submit.
    """

    def __init__(
        self,
        root,
        *,
        profile_path=None,
        service_factory=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.profile_path=(
            Path(profile_path)
            if profile_path is not None
            else self.root/"release"/"v14001_15000_paper_autonomous_execution"/
                 "config"/"paper_execution_profile.json"
        )
        self.output_dir=self.root/"release"/"v14001_15000_paper_autonomous_execution"
        self.v2121_latest=(
            self.root/"runtime"/"actual_intraday_canonical_e2e_v2_1_21"/
            "latest_validation.json"
        )
        self.qualification_latest=(
            self.root/"runtime"/"sandbox_readiness_gate_v2_1_17"/
            "latest_qualification.json"
        )
        self.canonical_snapshot=(
            self.root/"runtime"/"real_market_multitimeframe_shadow"/
            "latest_real_market_shadow.json"
        )

        self.runtime_dir=(
            self.root/"runtime"/"alpaca_paper_bounded_execution_v2_1_22"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.plan_path=self.runtime_dir/"latest_plan.json"
        self.ledger=self.runtime_dir/"execution_ledger.jsonl"

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

    def _write_plan(self,row):
        self.plan_path.write_text(
            json.dumps(row,indent=2,sort_keys=True,ensure_ascii=False,default=str),
            encoding="utf-8",
        )
        return row

    def _append(self,row):
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(row,sort_keys=True,ensure_ascii=False,default=str)
                +"\n"
            )

    def _submission_rows(self):
        if not self.ledger.exists():
            return []
        rows=[]
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            if row.get("paper_order_submitted") is True:
                rows.append(row)
        return rows

    def _submitted_evidence_keys(self):
        return {
            str(row.get("evidence_key") or "")
            for row in self._submission_rows()
            if row.get("evidence_key")
        }

    def _today_submission_count(self,now):
        day=now.date()
        count=0
        for row in self._submission_rows():
            ts=row.get("submitted_at_utc")
            if not ts:
                continue
            try:
                dt=datetime.fromisoformat(str(ts).replace("Z","+00:00"))
                if dt.astimezone(timezone.utc).date()==day:
                    count+=1
            except Exception:
                continue
        return count

    def build_plan(self):
        if not self.profile_path.exists():
            return self._write_plan({
                "status":"BLOCKED_PROFILE_MISSING",
                "profile_path":str(self.profile_path),
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        profile=PaperExecutionProfile.load(self.profile_path)
        profile_errors=profile.validate()
        if profile_errors:
            return self._write_plan({
                "status":"BLOCKED_PROFILE_INVALID",
                "profile_errors":profile_errors,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if not self.v2121_latest.exists():
            return self._write_plan({
                "status":"WAITING_FOR_V2_1_21_CURRENT_READY",
                "reason":"V2_1_21_VALIDATION_MISSING",
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        v2121=self._read_json(self.v2121_latest)
        if (
            v2121.get("status")!="PASS_ACTUAL_INTRADAY_CANONICAL_READY"
            or v2121.get("ready_for_manual_sandbox_review") is not True
        ):
            return self._write_plan({
                "status":"WAITING_FOR_V2_1_21_CURRENT_READY",
                "reason":str(v2121.get("status") or "NOT_READY"),
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if not self.qualification_latest.exists():
            return self._write_plan({
                "status":"BLOCKED_CURRENT_QUALIFICATION_MISSING",
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        q=self._read_json(self.qualification_latest)
        evidence_key=str(q.get("evidence_key") or "").strip()
        if not evidence_key:
            return self._write_plan({
                "status":"BLOCKED_EVIDENCE_KEY_MISSING",
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        v21q=v2121.get("latest_qualification") or {}
        if str(v21q.get("evidence_key") or "")!=evidence_key:
            return self._write_plan({
                "status":"BLOCKED_CURRENT_EVIDENCE_BINDING_MISMATCH",
                "v2_1_21_evidence_key":v21q.get("evidence_key"),
                "current_qualification_evidence_key":evidence_key,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if not (
            q.get("ready") is True
            and q.get("qualification_status")=="READY_FOR_MANUAL_SANDBOX_REVIEW"
            and q.get("canonical_paper_gate_semantics")=="CORRECTED_V2_1_19_1"
            and str(q.get("canonical_min_confidence"))=="0.75"
            and str(q.get("canonical_min_reward_risk"))=="1.0"
        ):
            return self._write_plan({
                "status":"BLOCKED_CANONICAL_QUALIFICATION_CONTRACT",
                "evidence_key":evidence_key,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if not self.canonical_snapshot.exists():
            return self._write_plan({
                "status":"BLOCKED_CANONICAL_SNAPSHOT_MISSING",
                "evidence_key":evidence_key,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        candidates=load_signal_candidates(self.canonical_snapshot)
        selected=select_candidate(
            candidates,
            allowed_symbols=profile.allowed_symbols,
            min_confidence=profile.min_confidence,
            min_reward_risk=profile.min_reward_risk,
            excluded_symbols=(),
        )

        if selected is None:
            return self._write_plan({
                "status":"NO_ACTION_NO_CANONICAL_CANDIDATE",
                "evidence_key":evidence_key,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        qsignals=list(q.get("signals") or [])
        matched=any(
            str(s.get("symbol") or "").upper()==str(selected.get("symbol") or "").upper()
            and str(s.get("side") or "").upper()==str(selected.get("side") or "").upper()
            for s in qsignals
        )
        if not matched:
            return self._write_plan({
                "status":"BLOCKED_SELECTED_CANDIDATE_NOT_IN_CURRENT_QUALIFICATION",
                "evidence_key":evidence_key,
                "selected_candidate":selected,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if str(selected.get("side") or "").lower()!="buy":
            return self._write_plan({
                "status":"NO_ACTION_SELL_DELEGATED_TO_POSITION_LIFECYCLE",
                "evidence_key":evidence_key,
                "selected_candidate":selected,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        if evidence_key in self._submitted_evidence_keys():
            return self._write_plan({
                "status":"BLOCKED_EVIDENCE_ALREADY_CONSUMED",
                "evidence_key":evidence_key,
                "selected_candidate":selected,
                "paper_order_submitted":False,
                "live_order_submitted":False,
            })

        fingerprint=hashlib.sha256(
            json.dumps(
                {
                    "evidence_key":evidence_key,
                    "selected_candidate":selected,
                    "profile":profile.profile_name,
                    "max_notional":profile.max_notional_per_order,
                },
                sort_keys=True,
                separators=(",",":"),
            ).encode("utf-8")
        ).hexdigest()

        return self._write_plan({
            "status":"READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION",
            "evidence_key":evidence_key,
            "selected_candidate":selected,
            "plan_fingerprint_sha256":fingerprint,
            "profile_name":profile.profile_name,
            "maximum_orders_per_session":profile.max_orders_per_session,
            "maximum_notional_per_order":profile.max_notional_per_order,
            "canonical_min_confidence":profile.min_confidence,
            "canonical_min_reward_risk":profile.min_reward_risk,
            "manual_paper_arm_required":profile.require_manual_arm_token,
            "paper_submission_enabled":profile.paper_submission_enabled,
            "live_submission_enabled":False,
            "paper_order_submitted":False,
            "live_order_submitted":False,
            "broker":"ALPACA_PAPER",
        })

    def execute_once(self,confirmation):
        plan=self.build_plan()
        if plan.get("status")!="READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION":
            return plan

        if confirmation!=CONFIRMATION_PHRASE:
            return self._write_plan({
                **plan,
                "status":"BLOCKED_EXPLICIT_PAPER_CONFIRMATION_REQUIRED",
                "required_confirmation":CONFIRMATION_PHRASE,
            })

        now=self.now_fn().astimezone(timezone.utc)
        profile=PaperExecutionProfile.load(self.profile_path)

        if self._today_submission_count(now)>=profile.max_orders_per_session:
            return self._write_plan({
                **plan,
                "status":"BLOCKED_LOCAL_SESSION_ORDER_LIMIT",
                "today_bridge_submission_count":self._today_submission_count(now),
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
            return self._write_plan(result)

        selected=plan["selected_candidate"]
        open_symbols=service.adapter.open_position_symbols()
        if str(selected["symbol"]).upper() in open_symbols:
            result={
                **plan,
                "status":"BLOCKED_EXISTING_OPEN_POSITION",
                "open_position_symbols":sorted(open_symbols),
            }
            self._append(result)
            return self._write_plan(result)

        evidence_key=plan["evidence_key"]
        client_order_id=(
            "paper-v2122-"
            +hashlib.sha256(evidence_key.encode("utf-8")).hexdigest()[:20]
        )

        order=service.adapter.submit_market_notional(
            symbol=selected["symbol"],
            side=selected["side"],
            notional=profile.max_notional_per_order,
            client_order_id=client_order_id,
        )

        result={
            **plan,
            "status":"PAPER_ORDER_SUBMITTED_BOUNDED",
            "preflight":preflight,
            "client_order_id":client_order_id,
            "order":order,
            "submitted_at_utc":now.isoformat(),
            "paper_order_submitted":True,
            "live_order_submitted":False,
            "paper_only":True,
        }
        self._append(result)
        self._write_plan(result)
        return result
