from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.challenger_shadow_execution_simulator_v2_2_7 import (
    ChallengerShadowExecutionSimulatorV227,
)
from ai_engine_v2.challenger_shadow_execution_simulator_status_v2_2_7 import (
    build_v2_2_7_status,
)


def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        "".join(json.dumps(x)+"\n" for x in rows),
        encoding="utf-8",
    )


def snap(sid,ts,price,symbol="AAPL"):
    return {
        "snapshot_id":sid,
        "observed_at_utc":ts,
        "symbol_rows":[{
            "symbol":symbol,
            "action":"BUY",
            "timeframes":[{
                "timeframe":"1m",
                "features":{"close":price},
            }],
        }],
    }


def comparison(
    sid="s1",
    ts="2026-08-10T16:00:00+00:00",
    classification="CHALLENGER_ONLY",
    action="BUY",
):
    return {
        "comparison_id":"cmp1",
        "feature_snapshot_id":sid,
        "feature_observed_at_utc":ts,
        "policy_source":"TEST",
        "comparisons":[{
            "challenger_policy":{
                "policy_id":"CHALLENGER_A",
                "min_confidence":.70,
                "min_reward_risk":1.15,
                "execution_enabled":False,
            },
            "symbol_comparisons":[{
                "symbol":"AAPL",
                "action":action,
                "classification":classification,
                "quality_score_shadow":.8,
                "canonical_analysis_sha256":"sha1",
            }],
        }],
    }


def setup_policy(root,stop=5,take=10,trailing=4):
    p=(
        Path(root)/"release"/"v95_33_to_v95_64"/"input"
    )
    p.mkdir(parents=True,exist_ok=True)
    (p/"position_lifecycle_policy.json").write_text(
        json.dumps({
            "stop_loss_pct":stop,
            "take_profit_pct":take,
            "trailing_stop_pct":trailing,
            "maximum_holding_days":20,
        }),
        encoding="utf-8",
    )


class Tests(unittest.TestCase):
    def paths(self,td):
        root=Path(td)
        fl=(
            root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"/
            "feature_snapshot_ledger.jsonl"
        )
        cl=(
            root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"/
            "comparison_ledger.jsonl"
        )
        return root,fl,cl

    def test_waiting_no_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            r=ChallengerShadowExecutionSimulatorV227(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_5_COMPARISON_LEDGER",
            )

    def test_take_profit_long(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,cl=self.paths(td)
            setup_policy(root,stop=5,take=2,trailing=4)
            write_jsonl(fl,[
                snap("s1","2026-08-10T16:00:00+00:00",100),
                snap("s2","2026-08-10T16:01:00+00:00",101),
                snap("s3","2026-08-10T16:02:00+00:00",102.5),
            ])
            write_jsonl(cl,[comparison()])
            c=ChallengerShadowExecutionSimulatorV227(root)
            r=c.build()
            self.assertEqual(r["new_completed_shadow_round_trips"],1)
            rows=c._read_jsonl(c.completed_ledger)
            sim=rows[0]["simulation"]
            self.assertEqual(sim["exit_reason"],"TAKE_PROFIT")
            self.assertGreater(sim["gross_pnl_before_fees"],0)

    def test_stop_loss_long(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,cl=self.paths(td)
            setup_policy(root,stop=2,take=10,trailing=4)
            write_jsonl(fl,[
                snap("s1","2026-08-10T16:00:00+00:00",100),
                snap("s2","2026-08-10T16:01:00+00:00",97),
            ])
            write_jsonl(cl,[comparison()])
            c=ChallengerShadowExecutionSimulatorV227(root)
            r=c.build()
            rows=c._read_jsonl(c.completed_ledger)
            self.assertEqual(
                rows[0]["simulation"]["exit_reason"],
                "STOP_LOSS",
            )
            self.assertLess(
                rows[0]["simulation"]["gross_pnl_before_fees"],0
            )

    def test_sell_profit(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,cl=self.paths(td)
            setup_policy(root,stop=5,take=2,trailing=4)
            write_jsonl(fl,[
                snap("s1","2026-08-10T16:00:00+00:00",100),
                snap("s2","2026-08-10T16:01:00+00:00",97),
            ])
            write_jsonl(cl,[comparison(action="SELL")])
            c=ChallengerShadowExecutionSimulatorV227(root)
            c.build()
            rows=c._read_jsonl(c.completed_ledger)
            self.assertGreater(
                rows[0]["simulation"]["gross_pnl_before_fees"],0
            )

    def test_non_challenger_only_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,cl=self.paths(td)
            setup_policy(root)
            write_jsonl(fl,[
                snap("s1","2026-08-10T16:00:00+00:00",100)
            ])
            write_jsonl(cl,[comparison(classification="BOTH")])
            r=ChallengerShadowExecutionSimulatorV227(root).build()
            self.assertEqual(r["challenger_only_signals"],0)
            self.assertEqual(r["new_completed_shadow_round_trips"],0)

    def test_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,cl=self.paths(td)
            setup_policy(root,stop=5,take=2)
            write_jsonl(fl,[
                snap("s1","2026-08-10T16:00:00+00:00",100),
                snap("s2","2026-08-10T16:01:00+00:00",103),
            ])
            write_jsonl(cl,[comparison()])
            c=ChallengerShadowExecutionSimulatorV227(root)
            a=c.build()
            b=c.build()
            self.assertEqual(a["new_completed_shadow_round_trips"],1)
            self.assertEqual(b["new_completed_shadow_round_trips"],0)
            self.assertEqual(b["duplicate_simulations"],1)

    def test_status_contract(self):
        s=build_v2_2_7_status()
        self.assertTrue(s["v2_2_1_feature_ledger_reused"])
        self.assertTrue(s["existing_position_exit_rule_reused"])
        self.assertTrue(s["counterfactual_shadow_execution"])
        self.assertFalse(s["actual_broker_fill_used"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
