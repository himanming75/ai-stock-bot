from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


APPROVAL_PHRASE="APPROVE_SANDBOX_REVIEW"


def utc_now():
    return datetime.now(timezone.utc)


def parse_utc(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def canonical_packet_fingerprint(packet):
    payload=json.dumps(
        packet,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ApprovalPolicyV2119:
    expires_minutes:int=15

    def validate(self):
        if self.expires_minutes < 1:
            raise ValueError("expires_minutes must be >= 1")
        if self.expires_minutes > 120:
            raise ValueError("expires_minutes must be <= 120")
        return self


class ManualApprovalRecordExpirationGuardV2119:
    """
    Records explicit human approval for a V2.1.18 review packet.

    Approval is evidence only. It does not start OAuth, Preview, Place,
    or any broker order.

    One-time-use state is initialized but not consumed by this stage.
    """

    def __init__(self,root,policy=None,now_fn=None):
        self.root=Path(root)
        self.policy=(policy or ApprovalPolicyV2119()).validate()
        self.now_fn=now_fn or utc_now

        self.packet_dir=(
            self.root
            /"runtime"
            /"manual_sandbox_review_packets_v2_1_18"
        )
        self.runtime_dir=(
            self.root
            /"runtime"
            /"manual_approval_v2_1_19"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.approval_ledger=self.runtime_dir/"approval_ledger.jsonl"
        self.latest_approval=self.runtime_dir/"latest_approval.json"

    def _approval_rows(self):
        if not self.approval_ledger.exists():
            return []
        rows=[]
        for line in self.approval_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _find_existing(self,evidence_key):
        for row in reversed(self._approval_rows()):
            if row.get("evidence_key")==evidence_key:
                return row
        return None

    def _packet_path(self,evidence_key):
        safe="".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in str(evidence_key)
        )[:80]
        return self.packet_dir/f"review_packet_{safe}.json"

    @staticmethod
    def _validate_packet(packet,evidence_key):
        reasons=[]

        if packet.get("packet_status")!="AWAITING_MANUAL_REVIEW":
            reasons.append("PACKET_NOT_AWAITING_MANUAL_REVIEW")
        if packet.get("evidence_key")!=evidence_key:
            reasons.append("EVIDENCE_KEY_MISMATCH")
        if packet.get("qualification_status")!="READY_FOR_MANUAL_SANDBOX_REVIEW":
            reasons.append("QUALIFICATION_NOT_READY")
        if packet.get("manual_review_required") is not True:
            reasons.append("MANUAL_REVIEW_NOT_REQUIRED")
        if packet.get("manual_approval_recorded") is not False:
            reasons.append("PACKET_ALREADY_MARKED_APPROVED")
        if packet.get("automatic_sandbox_execution_allowed") is not False:
            reasons.append("AUTO_SANDBOX_EXECUTION_NOT_LOCKED")
        if int(packet.get("broker_orders_submitted") or 0)!=0:
            reasons.append("PACKET_BROKER_ORDER_COUNT_NOT_ZERO")
        if packet.get("production_order_submission") is not False:
            reasons.append("PACKET_PROD_NOT_LOCKED")
        if packet.get("live_trading") is not False:
            reasons.append("PACKET_LIVE_NOT_LOCKED")

        signals=list(packet.get("signals") or [])
        if int(packet.get("eligible_signal_count") or 0)!=len(signals):
            reasons.append("PACKET_SIGNAL_COUNT_MISMATCH")
        if not signals:
            reasons.append("PACKET_HAS_NO_SIGNALS")

        return reasons

    def approve(self,evidence_key,approval_phrase,approved_by="LOCAL_USER"):
        evidence_key=str(evidence_key or "").strip()
        if not evidence_key:
            return {
                "status":"NOT_APPROVED",
                "reason":"MISSING_EVIDENCE_KEY",
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        if approval_phrase!=APPROVAL_PHRASE:
            return {
                "status":"NOT_APPROVED",
                "reason":"EXPLICIT_APPROVAL_PHRASE_REQUIRED",
                "required_phrase":APPROVAL_PHRASE,
                "evidence_key":evidence_key,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        existing=self._find_existing(evidence_key)
        if existing is not None:
            return {
                "status":"NOT_APPROVED_DUPLICATE",
                "reason":"APPROVAL_ALREADY_RECORDED_FOR_EVIDENCE",
                "evidence_key":evidence_key,
                "existing_approval_id":existing.get("approval_id"),
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        packet_path=self._packet_path(evidence_key)
        if not packet_path.exists():
            return {
                "status":"WAITING_FOR_V2_1_18_REVIEW_PACKET",
                "evidence_key":evidence_key,
                "packet_path":str(packet_path),
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        packet=json.loads(packet_path.read_text(encoding="utf-8"))
        reasons=self._validate_packet(packet,evidence_key)
        if reasons:
            return {
                "status":"NOT_APPROVED_PACKET_VALIDATION_FAILED",
                "evidence_key":evidence_key,
                "reasons":reasons,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        now=self.now_fn()
        if now.tzinfo is None:
            raise ValueError("now_fn must return timezone-aware datetime")
        now=now.astimezone(timezone.utc)

        expires=now+timedelta(
            minutes=self.policy.expires_minutes
        )
        fingerprint=canonical_packet_fingerprint(packet)

        approval_id=hashlib.sha256(
            (
                evidence_key
                +"|"
                +fingerprint
                +"|"
                +now.isoformat()
            ).encode("utf-8")
        ).hexdigest()[:24]

        record={
            "stage":
                "BROKER_INTEGRATION_V2_1_19_MANUAL_APPROVAL_RECORD_EXPIRATION_GUARD",
            "approval_id":approval_id,
            "approval_status":"APPROVED_NOT_CONSUMED",
            "evidence_key":evidence_key,
            "approved_by":str(approved_by or "LOCAL_USER"),
            "approved_at_utc":now.isoformat(),
            "expires_at_utc":expires.isoformat(),
            "expires_minutes":self.policy.expires_minutes,
            "packet_path":str(packet_path),
            "packet_fingerprint_sha256":fingerprint,
            "signals":list(packet.get("signals") or []),
            "manual_approval_recorded":True,
            "approval_consumed":False,
            "usage_count":0,
            "one_time_use":True,
            "automatic_sandbox_execution_allowed":False,
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }

        with self.approval_ledger.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(
                    record,
                    sort_keys=True,
                    ensure_ascii=False,
                )+"\n"
            )

        self.latest_approval.write_text(
            json.dumps(
                record,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "status":"PASS_MANUAL_APPROVAL_RECORDED",
            **record,
            "approval_ledger":str(self.approval_ledger),
            "latest_approval":str(self.latest_approval),
        }

    def validate_approval(self,evidence_key,now_utc=None):
        evidence_key=str(evidence_key or "").strip()
        row=self._find_existing(evidence_key)
        if row is None:
            return {
                "status":"NOT_READY_NO_APPROVAL",
                "evidence_key":evidence_key,
                "ready_for_one_time_manual_sandbox_handoff":False,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        now=now_utc or self.now_fn()
        if now.tzinfo is None:
            raise ValueError("now timestamp must be timezone-aware")
        now=now.astimezone(timezone.utc)
        expires=parse_utc(row["expires_at_utc"])

        reasons=[]
        if now >= expires:
            reasons.append("APPROVAL_EXPIRED")
        if row.get("approval_consumed") is not False:
            reasons.append("APPROVAL_ALREADY_CONSUMED")
        if int(row.get("usage_count") or 0)!=0:
            reasons.append("APPROVAL_USAGE_COUNT_NOT_ZERO")
        if row.get("one_time_use") is not True:
            reasons.append("ONE_TIME_USE_FLAG_NOT_TRUE")
        if row.get("automatic_sandbox_execution_allowed") is not False:
            reasons.append("AUTO_EXECUTION_NOT_LOCKED")

        packet_path=Path(row.get("packet_path") or "")
        if not packet_path.exists():
            reasons.append("REVIEW_PACKET_MISSING")
        else:
            packet=json.loads(packet_path.read_text(encoding="utf-8"))
            current=canonical_packet_fingerprint(packet)
            if current!=row.get("packet_fingerprint_sha256"):
                reasons.append("REVIEW_PACKET_FINGERPRINT_CHANGED")

        ready=len(reasons)==0

        return {
            "status":(
                "READY_FOR_ONE_TIME_MANUAL_SANDBOX_HANDOFF"
                if ready
                else "NOT_READY"
            ),
            "evidence_key":evidence_key,
            "approval_id":row.get("approval_id"),
            "approved_at_utc":row.get("approved_at_utc"),
            "expires_at_utc":row.get("expires_at_utc"),
            "ready_for_one_time_manual_sandbox_handoff":ready,
            "reasons":reasons,
            "approval_consumed":row.get("approval_consumed"),
            "usage_count":row.get("usage_count"),
            "one_time_use":row.get("one_time_use"),
            "automatic_sandbox_execution_allowed":False,
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }
