from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.champion_challenger_outcome_comparator_v2_2_6 import (
    ChampionChallengerOutcomeComparatorV226,
)
from ai_engine_v2.champion_challenger_outcome_comparator_status_v2_2_6 import (
    build_v2_2_6_status,
)


def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        "".join(json.dumps(x)+"\n" for x in rows),
        encoding="utf-8",
    )


def outcome(rid,sid="snap1",symbol="AAPL",label="WIN",pnl="2",ret=".2"):
    return {
        "status":"LABELED_BOUND_PAPER_OUTCOME",
        "round_trip_id":rid,
        "evidence_key":"ev",
        "symbol":symbol,
        "outcome":{
            "outcome_label":label,
            "gross_pnl_from_fills":pnl,
            "return_pct_from_fills":ret,
            "holding_seconds":600,
            "exit_reason":"TAKE_PROFIT" if label=="WIN" else "STOP_LOSS",
        },
        "feature_binding":{
            "snapshot_id":sid,
        },
        "training_record_sha256":"train-"+rid,
    }


def comparison(
    sid="snap1",
    *,
    classification="BOTH",
    symbol="AAPL",
    pid="SEED_CHALLENGER_A",
):
    return {
        "status":"PASS_CHAMPION_CHALLENGER_SHADOW_COMPARISON",
        "comparison_id":"cmp-"+sid+"-"+pid,
        "feature_snapshot_id":sid,
        "feature_observed_at_utc":"2026-08-10T16:00:00+00:00",
        "policy_source":"SEED_TEST",
        "comparisons":[{
            "challenger_policy":{
                "policy_id":pid,
                "min_confidence":.70,
                "min_reward_risk":1.15,
                "execution_enabled":False,
            },
            "symbol_comparisons":[{
                "symbol":symbol,
                "action":"BUY",
                "classification":classification,
            }],
        }],
    }


class Tests(unittest.TestCase):
    def paths(self,td):
        root=Path(td)
        op=(
            root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
            "labeled_outcomes.jsonl"
        )
        cp=(
            root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"/
            "comparison_ledger.jsonl"
        )
        return root,op,cp

    def test_waiting_no_outcome(self):
        with tempfile.TemporaryDirectory() as td:
            r=ChampionChallengerOutcomeComparatorV226(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
            )
            self.assertFalse(r["counterfactual_pnl_fabricated"])

    def test_waiting_no_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[outcome("rt1")])
            r=ChampionChallengerOutcomeComparatorV226(root).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_5_COMPARISON_LEDGER",
            )

    def test_both_realized_outcome(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[outcome("rt1")])
            write_jsonl(cp,[comparison(classification="BOTH")])
            c=ChampionChallengerOutcomeComparatorV226(root)
            r=c.build()
            self.assertEqual(
                r["status"],
                "PASS_CHAMPION_CHALLENGER_OUTCOME_COMPARISON",
            )
            p=r["per_challenger"]["SEED_CHALLENGER_A"]
            self.assertEqual(p["realized_both"]["trades"],1)
            self.assertEqual(
                p["realized_both"]["gross_pnl_before_fees"],2.0
            )
            self.assertEqual(
                p["realized_champion_only"]["trades"],0
            )
            self.assertFalse(r["counterfactual_pnl_fabricated"])

    def test_champion_only_realized_outcome(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[
                outcome("rt1",label="LOSS",pnl="-1",ret="-.1")
            ])
            write_jsonl(cp,[comparison(classification="CHAMPION_ONLY")])
            r=ChampionChallengerOutcomeComparatorV226(root).build()
            p=r["per_challenger"]["SEED_CHALLENGER_A"]
            self.assertEqual(
                p["realized_champion_only"]["trades"],1
            )
            self.assertEqual(
                p["realized_champion_only"]["losses"],1
            )

    def test_challenger_only_is_coverage_not_fake_pnl(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[outcome("rt1")])
            cmp=comparison(classification="BOTH")
            cmp2=comparison(
                sid="snap2",
                classification="CHALLENGER_ONLY",
            )
            write_jsonl(cp,[cmp,cmp2])
            r=ChampionChallengerOutcomeComparatorV226(root).build()
            p=r["per_challenger"]["SEED_CHALLENGER_A"]
            self.assertEqual(
                p["challenger_only_shadow_signal_count"],1
            )
            self.assertFalse(
                p["challenger_only_realized_outcomes_available"]
            )
            self.assertFalse(r["counterfactual_pnl_fabricated"])

    def test_exact_snapshot_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[outcome("rt1",sid="snapX")])
            write_jsonl(cp,[comparison(sid="snap1")])
            c=ChampionChallengerOutcomeComparatorV226(root)
            r=c.build()
            self.assertEqual(r["new_bound_policy_outcome_rows"],0)
            self.assertEqual(r["unbound_actual_outcomes"],1)
            rows=c._read_jsonl(c.unbound_ledger)
            self.assertEqual(
                rows[0]["reason"],
                "NO_EXACT_FEATURE_SNAPSHOT_COMPARISON",
            )

    def test_sample_guard(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            outs=[]
            cmps=[]
            for i in range(5):
                sid=f"s{i}"
                outs.append(outcome(f"rt{i}",sid=sid))
                cmps.append(comparison(sid=sid))
            write_jsonl(op,outs)
            write_jsonl(cp,cmps)
            r=ChampionChallengerOutcomeComparatorV226(root).build()
            p=r["per_challenger"]["SEED_CHALLENGER_A"]
            self.assertTrue(p["outcome_sample_qualified"])
            self.assertTrue(p["promotion_evidence_ready"])
            self.assertFalse(r["promotion_enabled"])

    def test_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            root,op,cp=self.paths(td)
            write_jsonl(op,[outcome("rt1")])
            write_jsonl(cp,[comparison()])
            c=ChampionChallengerOutcomeComparatorV226(root)
            a=c.build()
            b=c.build()
            self.assertEqual(a["new_bound_policy_outcome_rows"],1)
            self.assertEqual(b["new_bound_policy_outcome_rows"],0)
            self.assertGreaterEqual(b["duplicate_bindings"],1)

    def test_status_contract(self):
        s=build_v2_2_6_status()
        self.assertTrue(s["exact_snapshot_id_binding"])
        self.assertTrue(s["both_realized_metrics"])
        self.assertTrue(s["champion_only_realized_metrics"])
        self.assertTrue(s["challenger_only_shadow_coverage"])
        self.assertFalse(s["counterfactual_pnl_fabricated"])
        self.assertFalse(s["promotion_enabled"])
        self.assertFalse(s["challenger_execution_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
