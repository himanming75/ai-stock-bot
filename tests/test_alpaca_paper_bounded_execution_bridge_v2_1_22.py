from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.alpaca_paper_bounded_execution_bridge_v2_1_22 import (
    AlpacaPaperBoundedExecutionBridgeV2122,
    CONFIRMATION_PHRASE,
)
from broker_integration_v1.alpaca_paper_bounded_execution_status_v2_1_22 import (
    build_v2_1_22_status,
)


EVIDENCE="fixture-current-ready-001"


def write_profile(root):
    p=Path(root)/"release"/"v14001_15000_paper_autonomous_execution"/"config"
    p.mkdir(parents=True,exist_ok=True)
    profile={
        "profile_name":"PAPER_AUTONOMOUS_VALIDATION_V1",
        "paper_submission_enabled":True,
        "live_submission_enabled":False,
        "max_orders_per_session":1,
        "max_notional_per_order":25.0,
        "allowed_symbols":["AAPL","MSFT","NVDA","SPY"],
        "min_confidence":0.75,
        "min_reward_risk":1.0,
        "poll_seconds":30,
        "require_market_open":True,
        "require_manual_arm_token":True,
    }
    (p/"paper_execution_profile.json").write_text(
        json.dumps(profile),encoding="utf-8"
    )


def write_ready_sources(root,evidence=EVIDENCE):
    root=Path(root)
    p21=root/"runtime"/"actual_intraday_canonical_e2e_v2_1_21"
    pq=root/"runtime"/"sandbox_readiness_gate_v2_1_17"
    ps=root/"runtime"/"real_market_multitimeframe_shadow"
    for p in (p21,pq,ps):
        p.mkdir(parents=True,exist_ok=True)

    qualification={
        "evidence_key":evidence,
        "ready":True,
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "canonical_paper_gate_semantics":"CORRECTED_V2_1_19_1",
        "canonical_min_confidence":"0.75",
        "canonical_min_reward_risk":"1.0",
        "signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"FIXTURE",
            "source_confidence":"0.82",
            "source_reward_risk":"1.25",
        }],
    }

    (pq/"latest_qualification.json").write_text(
        json.dumps(qualification),encoding="utf-8"
    )

    v21={
        "status":"PASS_ACTUAL_INTRADAY_CANONICAL_READY",
        "ready_for_manual_sandbox_review":True,
        "latest_qualification":{
            "evidence_key":evidence,
            "ready":True,
            "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        },
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (p21/"latest_validation.json").write_text(
        json.dumps(v21),encoding="utf-8"
    )

    canonical={
        "analyses":[{
            "symbol":"AAPL",
            "action":"BUY",
            "execution_mode":"ANALYSIS_ONLY",
            "reward_risk":1.25,
            "consensus_score":0.7,
            "confidence_calibration":{"calibrated_confidence":0.82},
        }],
    }
    (ps/"latest_real_market_shadow.json").write_text(
        json.dumps(canonical),encoding="utf-8"
    )


class FakeAdapter:
    def __init__(self):
        self.submit_calls=[]
        self.open_symbols=set()

    def open_position_symbols(self):
        return set(self.open_symbols)

    def submit_market_notional(self,**kwargs):
        self.submit_calls.append(kwargs)
        return {
            "id":"paper-order-fixture",
            "client_order_id":kwargs["client_order_id"],
            "symbol":kwargs["symbol"],
            "side":kwargs["side"],
            "status":"accepted",
            "paper":True,
        }


class FakeService:
    def __init__(self,preflight_status="PASS"):
        self.adapter=FakeAdapter()
        self.preflight_status=preflight_status

    def preflight(self):
        return {
            "status":self.preflight_status,
            "paper":True,
            "market_open":True,
            "arm_token_valid":True,
            "live_submission_enabled":False,
        }


class Tests(unittest.TestCase):
    def test_waits_without_v2121(self):
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            b=AlpacaPaperBoundedExecutionBridgeV2122(td)
            r=b.build_plan()
            self.assertEqual(r["status"],"WAITING_FOR_V2_1_21_CURRENT_READY")
            self.assertFalse(r["paper_order_submitted"])

    def test_ready_plan_uses_existing_canonical_selector(self):
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            write_ready_sources(td)
            b=AlpacaPaperBoundedExecutionBridgeV2122(td)
            r=b.build_plan()
            self.assertEqual(r["status"],"READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION")
            self.assertEqual(r["selected_candidate"]["symbol"],"AAPL")
            self.assertEqual(r["selected_candidate"]["side"],"buy")
            self.assertEqual(r["maximum_notional_per_order"],25.0)
            self.assertFalse(r["paper_order_submitted"])

    def test_evidence_binding_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            write_ready_sources(td)
            p=Path(td)/"runtime"/"actual_intraday_canonical_e2e_v2_1_21"/"latest_validation.json"
            row=json.loads(p.read_text())
            row["latest_qualification"]["evidence_key"]="different"
            p.write_text(json.dumps(row))
            b=AlpacaPaperBoundedExecutionBridgeV2122(td)
            r=b.build_plan()
            self.assertEqual(r["status"],"BLOCKED_CURRENT_EVIDENCE_BINDING_MISMATCH")

    def test_confirmation_required(self):
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            write_ready_sources(td)
            b=AlpacaPaperBoundedExecutionBridgeV2122(td)
            r=b.execute_once("WRONG")
            self.assertEqual(r["status"],"BLOCKED_EXPLICIT_PAPER_CONFIRMATION_REQUIRED")

    def test_fake_paper_submit_exactly_once(self):
        fixed=datetime(2026,8,10,15,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            write_ready_sources(td)
            service=FakeService()
            b=AlpacaPaperBoundedExecutionBridgeV2122(
                td,
                service_factory=lambda:service,
                now_fn=lambda:fixed,
            )
            first=b.execute_once(CONFIRMATION_PHRASE)
            self.assertEqual(first["status"],"PAPER_ORDER_SUBMITTED_BOUNDED")
            self.assertTrue(first["paper_order_submitted"])
            self.assertFalse(first["live_order_submitted"])
            self.assertEqual(len(service.adapter.submit_calls),1)
            self.assertEqual(service.adapter.submit_calls[0]["notional"],25.0)

            second=b.execute_once(CONFIRMATION_PHRASE)
            self.assertEqual(second["status"],"BLOCKED_EVIDENCE_ALREADY_CONSUMED")
            self.assertEqual(len(service.adapter.submit_calls),1)

    def test_preflight_block_does_not_submit(self):
        fixed=datetime(2026,8,10,15,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            write_profile(td)
            write_ready_sources(td)
            service=FakeService("BLOCKED")
            b=AlpacaPaperBoundedExecutionBridgeV2122(
                td,
                service_factory=lambda:service,
                now_fn=lambda:fixed,
            )
            r=b.execute_once(CONFIRMATION_PHRASE)
            self.assertEqual(r["status"],"BLOCKED_PAPER_PREFLIGHT")
            self.assertEqual(len(service.adapter.submit_calls),0)

    def test_status_contract(self):
        s=build_v2_1_22_status()
        self.assertTrue(s["existing_alpaca_paper_adapter_reused"])
        self.assertFalse(s["new_broker_adapter_created"])
        self.assertFalse(s["new_order_request_engine_created"])
        self.assertEqual(s["maximum_validation_notional"],25.0)
        self.assertEqual(s["maximum_bridge_submissions_per_session"],1)
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_order_submission_allowed"])
        self.assertFalse(s["etrade_write_allowed"])


if __name__=="__main__":
    unittest.main()
