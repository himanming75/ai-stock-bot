from pathlib import Path
import json,tempfile,sys,unittest
from datetime import datetime,timezone,timedelta

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.threshold_sensitivity_shadow_audit_v2_1_31_4 import (
    ThresholdSensitivityShadowAuditV21314,
)
from broker_integration_v1.threshold_sensitivity_shadow_audit_status_v2_1_31_4 import (
    build_v2_1_31_4_status,
)


def make_snap(ts,conf=.64,rr=1.1,action="BUY",price=100.0,symbol="MSFT",sid="x"):
    return {
        "snapshot_id":sid,
        "observed_at_utc":ts.isoformat().replace("+00:00","Z"),
        "symbol_rows":[{
            "symbol":symbol,
            "action":action,
            "reward_risk":rr,
            "confidence_calibration":{"calibrated_confidence":conf},
            "selector_explanation":{
                "current_selector_inputs":{
                    "action":action,
                    "calibrated_confidence":conf,
                    "reward_risk":rr,
                    "min_confidence":.75,
                    "min_reward_risk":1.0,
                }
            },
            "timeframes":[{
                "timeframe":"1m",
                "features":{"close":price},
            }],
        }],
    }


class Tests(unittest.TestCase):
    def setup_policy(self,root):
        p=Path(root)/"release"/"broker_integration_v2_1_31_4_threshold_sensitivity_shadow_audit"/"config"
        p.mkdir(parents=True,exist_ok=True)
        (p/"threshold_sensitivity_policy.json").write_text(json.dumps({
            "confidence_thresholds":[.60,.65,.70,.75],
            "min_reward_risk":1.0,
            "horizons_minutes":[5,15,30,60],
            "resolution_tolerance_minutes":3,
            "continuous_poll_seconds":60,
            "continuous_max_runtime_seconds":3600,
            "action_filter":["BUY","SELL"],
            "actual_execution_threshold_unchanged":.75,
            "actual_execution_threshold_modified":False,
        }),encoding="utf-8")

    def test_waiting_without_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            self.setup_policy(td)
            r=ThresholdSensitivityShadowAuditV21314(td).audit()
            self.assertEqual(r["status"],"WAITING_FOR_V2_2_1_FEATURE_SNAPSHOTS")
            self.assertFalse(r["actual_execution_threshold_modified"])

    def test_threshold_signal_counts(self):
        with tempfile.TemporaryDirectory() as td:
            self.setup_policy(td)
            c=ThresholdSensitivityShadowAuditV21314(td)
            c.feature_ledger.parent.mkdir(parents=True,exist_ok=True)
            t=datetime(2026,8,10,15,0,tzinfo=timezone.utc)
            snaps=[
                make_snap(t,.64,1.1,"BUY",100,"MSFT","a"),
                make_snap(t+timedelta(minutes=5),.64,1.1,"BUY",101,"MSFT","b"),
            ]
            with c.feature_ledger.open("w",encoding="utf-8") as f:
                for s in snaps: f.write(json.dumps(s)+"\n")
            r=c.audit()
            self.assertEqual(r["thresholds"]["0.60"]["signal_count"],2)
            self.assertEqual(r["thresholds"]["0.65"]["signal_count"],0)
            self.assertEqual(r["thresholds"]["0.75"]["signal_count"],0)
            m=r["thresholds"]["0.60"]["horizons"]["5m"]
            self.assertEqual(m["resolved_count"],1)
            self.assertGreater(m["average_signed_return_pct"],0)

    def test_sell_signed_return(self):
        with tempfile.TemporaryDirectory() as td:
            self.setup_policy(td)
            c=ThresholdSensitivityShadowAuditV21314(td)
            c.feature_ledger.parent.mkdir(parents=True,exist_ok=True)
            t=datetime(2026,8,10,15,0,tzinfo=timezone.utc)
            with c.feature_ledger.open("w",encoding="utf-8") as f:
                f.write(json.dumps(make_snap(t,.8,1.2,"SELL",100,"AAPL","a"))+"\n")
                f.write(json.dumps(make_snap(t+timedelta(minutes=5),.8,1.2,"SELL",99,"AAPL","b"))+"\n")
            r=c.audit()
            m=r["thresholds"]["0.75"]["horizons"]["5m"]
            self.assertEqual(m["resolved_count"],1)
            self.assertGreater(m["average_signed_return_pct"],0)

    def test_rr_gate_held_constant(self):
        with tempfile.TemporaryDirectory() as td:
            self.setup_policy(td)
            c=ThresholdSensitivityShadowAuditV21314(td)
            c.feature_ledger.parent.mkdir(parents=True,exist_ok=True)
            t=datetime(2026,8,10,15,0,tzinfo=timezone.utc)
            with c.feature_ledger.open("w",encoding="utf-8") as f:
                f.write(json.dumps(make_snap(t,.9,.9,"BUY",100,"SPY","a"))+"\n")
            r=c.audit()
            self.assertTrue(all(v["signal_count"]==0 for v in r["thresholds"].values()))

    def test_policy_guard(self):
        with tempfile.TemporaryDirectory() as td:
            self.setup_policy(td)
            c=ThresholdSensitivityShadowAuditV21314(td)
            p=json.loads(c.policy_path.read_text())
            p["actual_execution_threshold_modified"]=True
            c.policy_path.write_text(json.dumps(p))
            with self.assertRaises(RuntimeError):
                c.policy()

    def test_status_contract(self):
        s=build_v2_1_31_4_status()
        self.assertEqual(s["threshold_grid"],[.60,.65,.70,.75])
        self.assertEqual(s["current_execution_threshold"],.75)
        self.assertFalse(s["execution_threshold_modified"])
        self.assertFalse(s["selector_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)


if __name__=="__main__":
    unittest.main()
