from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
    ApprovalPolicyV2119,
    APPROVAL_PHRASE,
)
from broker_integration_v1.manual_approval_record_expiration_guard_status_v2_1_19 import (
    build_v2_1_19_status,
)


def write_packet(root,key="ev1"):
    p=Path(root)/"runtime"/"manual_sandbox_review_packets_v2_1_18"
    p.mkdir(parents=True,exist_ok=True)
    safe="".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:80]
    packet={
        "stage":"BROKER_INTEGRATION_V2_1_18_MANUAL_SANDBOX_REVIEW_PACKET",
        "packet_status":"AWAITING_MANUAL_REVIEW",
        "evidence_key":key,
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "canonical_min_confidence":"0.60",
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"TEST",
            "source_confidence":"0.65",
        }],
        "qualification_reasons":[],
        "manual_review_required":True,
        "manual_approval_recorded":False,
        "automatic_sandbox_execution_allowed":False,
        "etrade_oauth_started":False,
        "sandbox_preview_sent":False,
        "sandbox_place_sent":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
        "profitability_validated":False,
    }
    path=p/f"review_packet_{safe}.json"
    path.write_text(json.dumps(packet),encoding="utf-8")
    return path


class TestV2119(unittest.TestCase):
    def test_phrase_required(self):
        with tempfile.TemporaryDirectory() as td:
            write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(td)
            r=g.approve("ev1","WRONG")
            self.assertEqual(r["status"],"NOT_APPROVED")
            self.assertEqual(r["broker_orders_submitted"],0)

    def test_approval_record(self):
        fixed=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(
                td,
                ApprovalPolicyV2119(expires_minutes=15),
                now_fn=lambda:fixed,
            )
            r=g.approve("ev1",APPROVAL_PHRASE)
            self.assertEqual(r["status"],"PASS_MANUAL_APPROVAL_RECORDED")
            self.assertFalse(r["approval_consumed"])
            self.assertEqual(r["usage_count"],0)
            self.assertTrue(r["one_time_use"])
            self.assertFalse(r["automatic_sandbox_execution_allowed"])

    def test_duplicate_approval_blocked(self):
        fixed=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(td,now_fn=lambda:fixed)
            a=g.approve("ev1",APPROVAL_PHRASE)
            b=g.approve("ev1",APPROVAL_PHRASE)
            self.assertEqual(a["status"],"PASS_MANUAL_APPROVAL_RECORDED")
            self.assertEqual(b["status"],"NOT_APPROVED_DUPLICATE")

    def test_expiration_guard(self):
        fixed=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(
                td,
                ApprovalPolicyV2119(expires_minutes=15),
                now_fn=lambda:fixed,
            )
            g.approve("ev1",APPROVAL_PHRASE)
            ok=g.validate_approval(
                "ev1",
                fixed+timedelta(minutes=10),
            )
            expired=g.validate_approval(
                "ev1",
                fixed+timedelta(minutes=16),
            )
            self.assertTrue(ok["ready_for_one_time_manual_sandbox_handoff"])
            self.assertFalse(expired["ready_for_one_time_manual_sandbox_handoff"])
            self.assertIn("APPROVAL_EXPIRED",expired["reasons"])

    def test_packet_fingerprint_change_blocks(self):
        fixed=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            path=write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(td,now_fn=lambda:fixed)
            g.approve("ev1",APPROVAL_PHRASE)
            packet=json.loads(path.read_text(encoding="utf-8"))
            packet["signals"][0]["quantity"]="2"
            path.write_text(json.dumps(packet),encoding="utf-8")
            r=g.validate_approval("ev1",fixed+timedelta(minutes=1))
            self.assertFalse(r["ready_for_one_time_manual_sandbox_handoff"])
            self.assertIn("REVIEW_PACKET_FINGERPRINT_CHANGED",r["reasons"])

    def test_status_locks(self):
        s=build_v2_1_19_status()
        self.assertTrue(s["explicit_approval_phrase_required"])
        self.assertTrue(s["packet_fingerprint_binding"])
        self.assertEqual(s["default_approval_expiration_minutes"],15)
        self.assertTrue(s["one_time_use_state_ready"])
        self.assertFalse(s["approval_consumption_from_stage"])
        self.assertFalse(s["automatic_sandbox_execution_allowed"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
