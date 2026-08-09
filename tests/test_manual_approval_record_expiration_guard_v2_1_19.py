from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
    APPROVAL_PHRASE,
)


def write_packet(root,key="ev1",legacy=False):
    p=Path(root)/"runtime"/"manual_sandbox_review_packets_v2_1_18"
    p.mkdir(parents=True,exist_ok=True)
    packet={
        "packet_status":"AWAITING_MANUAL_REVIEW",
        "evidence_key":key,
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "generic_etrade_bridge_min_confidence":"0.60",
        "canonical_min_confidence":"0.60" if legacy else "0.75",
        "canonical_min_reward_risk":None if legacy else "1.0",
        "canonical_paper_gate_semantics":None if legacy else "CORRECTED_V2_1_19_1",
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"AAPL","side":"BUY","quantity":"1","strategy_id":"TEST",
            "source_confidence":"0.80","source_reward_risk":"1.20" if not legacy else None,
        }],
        "manual_review_required":True,
        "manual_approval_recorded":False,
        "automatic_sandbox_execution_allowed":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (p/f"review_packet_{key}.json").write_text(json.dumps(packet),encoding="utf-8")


class TestCorrectedV2119(unittest.TestCase):
    def test_corrected_packet_can_record_approval(self):
        now=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_packet(td)
            g=ManualApprovalRecordExpirationGuardV2119(td,now_fn=lambda:now)
            r=g.approve("ev1",APPROVAL_PHRASE)
            self.assertEqual(r["status"],"PASS_MANUAL_APPROVAL_RECORDED")
            v=g.validate_approval("ev1",now+timedelta(minutes=1))
            self.assertTrue(v["ready_for_one_time_manual_sandbox_handoff"])

    def test_legacy_packet_is_blocked(self):
        now=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_packet(td,legacy=True)
            g=ManualApprovalRecordExpirationGuardV2119(td,now_fn=lambda:now)
            r=g.approve("ev1",APPROVAL_PHRASE)
            self.assertEqual(r["status"],"NOT_APPROVED_PACKET_VALIDATION_FAILED")

if __name__=="__main__":
    unittest.main()
