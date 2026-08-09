from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
    APPROVAL_PHRASE,
)

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"runtime"/"manual_sandbox_review_packets_v2_1_18"
    p.mkdir(parents=True,exist_ok=True)
    packet={
        "stage":"V2.1.18",
        "packet_status":"AWAITING_MANUAL_REVIEW",
        "evidence_key":"fixture-ready-001",
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "canonical_min_confidence":"0.60",
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"SPY",
            "side":"SELL",
            "quantity":"1",
            "strategy_id":"FIXTURE",
            "source_confidence":"0.66",
        }],
        "manual_review_required":True,
        "manual_approval_recorded":False,
        "automatic_sandbox_execution_allowed":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (p/"review_packet_fixture-ready-001.json").write_text(
        json.dumps(packet),
        encoding="utf-8",
    )

    now=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
    g=ManualApprovalRecordExpirationGuardV2119(
        td,
        now_fn=lambda:now,
    )
    r=g.approve(
        "fixture-ready-001",
        APPROVAL_PHRASE,
        approved_by="FIXTURE_USER",
    )
    v=g.validate_approval(
        "fixture-ready-001",
        now+timedelta(minutes=1),
    )

    print("APPROVAL STATUS:",r["status"])
    print("APPROVAL ID:",r["approval_id"])
    print("EXPIRES AT:",r["expires_at_utc"])
    print("CONSUMED:",r["approval_consumed"])
    print("USAGE COUNT:",r["usage_count"])
    print("VALIDATION:",v["status"])
    print("READY FOR HANDOFF:",v["ready_for_one_time_manual_sandbox_handoff"])
    print("AUTO EXECUTION:",v["automatic_sandbox_execution_allowed"])
    print("BROKER ORDERS:",v["broker_orders_submitted"])
    print("PROD:",v["production_order_submission"])
    print("LIVE:",v["live_trading"])
    assert v["ready_for_one_time_manual_sandbox_handoff"] is True
    assert v["broker_orders_submitted"]==0

print("V2.1.19 SYNTHETIC APPROVAL GUARD: PASS")
