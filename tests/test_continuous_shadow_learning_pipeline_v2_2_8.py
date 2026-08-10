from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.continuous_shadow_learning_pipeline_v2_2_8 import (
    ContinuousShadowLearningPipelineV228,
)
from ai_engine_v2.continuous_shadow_learning_pipeline_status_v2_2_8 import (
    build_v2_2_8_status,
)


class Clock:
    def __init__(self):
        self.t=datetime(2026,8,10,16,0,tzinfo=timezone.utc)
    def now(self):
        return self.t
    def sleep(self,seconds):
        self.t+=timedelta(seconds=seconds)


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")


class FakePipeline(ContinuousShadowLearningPipelineV228):
    def __init__(self,*args,fail_stage=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.calls=[]
        self.fail_stage=fail_stage

    def _pipeline_stages(self):
        out=[]
        for name in ("A","B","C"):
            def fn(n=name):
                self.calls.append(n)
                if n==self.fail_stage:
                    return {"status":"BLOCKED_TEST_STAGE"}
                return {"status":"PASS_TEST_STAGE"}
            out.append((name,fn))
        return out

    def build_scorecard(self):
        row={
            "champion_actual":{"completed_outcomes":0},
            "challenger_shadow":{"completed_counterfactual_round_trips":0},
            "calibration_ready":False,
            "promotion_evidence_ready":False,
            "promotion_enabled":False,
            "automatic_policy_change_enabled":False,
            "challenger_broker_execution_enabled":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        row["scorecard_sha256"]="test"
        return row


class Tests(unittest.TestCase):
    def test_input_change_detection_and_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            clock=Clock()
            c=FakePipeline(root,now_fn=clock.now,sleep_fn=clock.sleep)
            write(c.canonical_shadow,'{"x":1}')
            a=c.run_cycle()
            b=c.run_cycle()
            self.assertEqual(a["status"],"PASS_CONTINUOUS_SHADOW_LEARNING_CYCLE")
            self.assertEqual(b["status"],"NO_CHANGE_SKIPPED")
            write(c.canonical_shadow,'{"x":2}')
            d=c.run_cycle()
            self.assertEqual(d["status"],"PASS_CONTINUOUS_SHADOW_LEARNING_CYCLE")
            self.assertEqual(d["cycles_completed"],2)

    def test_actual_trade_change_also_triggers_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            c=FakePipeline(root)
            write(c.canonical_shadow,'{"x":1}')
            c.run_cycle()
            write(c.completed_actual,'{"round_trip_id":"1"}\n')
            r=c.run_cycle()
            self.assertEqual(r["status"],"PASS_CONTINUOUS_SHADOW_LEARNING_CYCLE")

    def test_fail_closed_stops_remaining_stages(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            c=FakePipeline(root,fail_stage="B")
            write(c.canonical_shadow,'{"x":1}')
            r=c.run_cycle()
            self.assertEqual(r["status"],"BLOCKED_SHADOW_LEARNING_STAGE_FAILURE")
            self.assertEqual(c.calls,["A","B"])

    def test_continuous_max_cycles(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            clock=Clock()
            c=FakePipeline(root,now_fn=clock.now,sleep_fn=clock.sleep)
            write(c.canonical_shadow,'{"x":1}')
            r=c.run_continuous(
                poll_seconds=5,
                max_runtime_seconds=100,
                max_cycles=1,
            )
            self.assertEqual(r["status"],"PASS_CONTINUOUS_SHADOW_LEARNING_SUPERVISOR")
            self.assertEqual(r["executed_cycles"],1)
            self.assertEqual(r["stop_reason"],"MAX_CYCLES")

    def test_stop_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            clock=Clock()
            c=FakePipeline(root,now_fn=clock.now,sleep_fn=clock.sleep)
            write(c.canonical_shadow,'{"x":1}')
            # stop file is cleared at supervisor start; create it after first sleep.
            def sleep_and_stop(seconds):
                clock.sleep(seconds)
                c.stop_file.write_text("stop",encoding="utf-8")
            c.sleep_fn=sleep_and_stop
            r=c.run_continuous(
                poll_seconds=5,
                max_runtime_seconds=100,
            )
            self.assertEqual(r["stop_reason"],"STOP_FILE")

    def test_scorecard_foundation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            c=ContinuousShadowLearningPipelineV228(root)
            labeled=(
                root/"runtime"/
                "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
                "labeled_outcomes.jsonl"
            )
            write(labeled,json.dumps({
                "status":"LABELED_BOUND_PAPER_OUTCOME",
                "outcome":{
                    "outcome_label":"WIN",
                    "gross_pnl_from_fills":"2.5",
                },
            })+"\n")
            shadow=(
                root/"runtime"/
                "ai_challenger_shadow_execution_simulator_v2_2_7"/
                "completed_shadow_round_trips.jsonl"
            )
            write(shadow,json.dumps({
                "simulation":{"gross_pnl_before_fees":-1.0}
            })+"\n")
            sc=c.build_scorecard()
            self.assertEqual(sc["champion_actual"]["completed_outcomes"],1)
            self.assertEqual(sc["champion_actual"]["wins"],1)
            self.assertEqual(
                sc["challenger_shadow"]["completed_counterfactual_round_trips"],1
            )
            self.assertEqual(sc["challenger_shadow"]["losses"],1)
            self.assertFalse(sc["promotion_enabled"])

    def test_status_contract(self):
        s=build_v2_2_8_status()
        self.assertTrue(s["v2_2_1_through_v2_2_7_orchestration"])
        self.assertTrue(s["canonical_shadow_change_detection"])
        self.assertTrue(s["actual_trade_ledger_change_detection"])
        self.assertTrue(s["continuous_supervisor"])
        self.assertTrue(s["fail_closed_stage_failure"])
        self.assertTrue(s["scorecard_foundation"])
        self.assertFalse(s["promotion_enabled"])
        self.assertFalse(s["automatic_policy_change_enabled"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
