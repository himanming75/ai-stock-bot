from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.threshold_calibration_challenger_policy_builder_v2_2_4 import (
    ThresholdCalibrationChallengerPolicyBuilderV224,
    CHAMPION_MIN_CONFIDENCE,
    CHAMPION_MIN_REWARD_RISK,
)
from ai_engine_v2.threshold_calibration_challenger_policy_builder_status_v2_2_4 import (
    build_v2_2_4_status,
)


def labeled(
    rid,
    *,
    label="WIN",
    pnl="2.0",
    ret="0.2",
    confidence=0.82,
    rr=1.4,
    regime="WEAK_BULL",
):
    return {
        "status":"LABELED_BOUND_PAPER_OUTCOME",
        "round_trip_id":rid,
        "symbol":"AAPL",
        "outcome":{
            "outcome_label":label,
            "gross_pnl_from_fills":pnl,
            "return_pct_from_fills":ret,
        },
        "feature_binding":{
            "reward_risk":rr,
            "market_regime":regime,
            "confidence_calibration":{
                "calibrated_confidence":confidence
            },
        },
    }


def write_source(root,rows):
    p=(
        Path(root)/"runtime"/
        "ai_outcome_labeling_feature_trade_binding_v2_2_2"
    )
    p.mkdir(parents=True,exist_ok=True)
    (p/"labeled_outcomes.jsonl").write_text(
        "".join(json.dumps(r)+"\n" for r in rows),
        encoding="utf-8",
    )


class Tests(unittest.TestCase):
    def test_waiting_without_outcomes(self):
        with tempfile.TemporaryDirectory() as td:
            c=ThresholdCalibrationChallengerPolicyBuilderV224(td)
            r=c.build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
            )
            self.assertFalse(r["promotion_enabled"])
            self.assertFalse(r["challenger_execution_enabled"])
            self.assertTrue(c.policy_json.exists())

    def test_champion_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[
                labeled(str(i)) for i in range(5)
            ])
            r=ThresholdCalibrationChallengerPolicyBuilderV224(td).build()
            self.assertEqual(
                r["champion"]["min_confidence"],
                CHAMPION_MIN_CONFIDENCE,
            )
            self.assertEqual(
                r["champion"]["min_reward_risk"],
                CHAMPION_MIN_REWARD_RISK,
            )
            self.assertFalse(r["champion_execution_modified"])
            self.assertFalse(r["execution_selector_modified"])

    def test_grid_and_top_challenger(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[
                labeled("1",confidence=.82,rr=1.4,pnl="2"),
                labeled("2",confidence=.84,rr=1.3,pnl="2"),
                labeled("3",confidence=.86,rr=1.5,pnl="3"),
                labeled("4",confidence=.88,rr=1.6,pnl="3"),
                labeled("5",confidence=.90,rr=1.8,pnl="4"),
                labeled(
                    "6",label="LOSS",confidence=.72,rr=.95,
                    pnl="-5",ret="-0.5",
                ),
            ]
            write_source(td,rows)
            c=ThresholdCalibrationChallengerPolicyBuilderV224(td)
            r=c.build()
            self.assertTrue(r["calibration_ready"])
            self.assertEqual(r["candidate_grid_size"],25)
            self.assertGreater(r["qualified_global_candidates"],0)
            self.assertGreater(len(r["top_global_challengers"]),0)
            self.assertFalse(r["promotion_enabled"])
            registry=json.loads(c.policy_json.read_text())
            self.assertFalse(registry["promotion_enabled"])
            self.assertFalse(registry["challenger_execution_enabled"])

    def test_regime_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[
                labeled(str(i),regime="WEAK_BULL")
                for i in range(5)
            ] + [
                labeled(
                    "x",regime="RANGE",label="LOSS",
                    pnl="-1",ret="-0.1",
                )
            ]
            write_source(td,rows)
            r=ThresholdCalibrationChallengerPolicyBuilderV224(td).build()
            by={x["market_regime"]:x for x in r["regime_challengers"]}
            self.assertIn("WEAK_BULL",by)
            self.assertIsNotNone(
                by["WEAK_BULL"].get("challenger_score")
            )
            self.assertEqual(
                by["RANGE"]["status"],
                "INSUFFICIENT_SAMPLE",
            )

    def test_status_contract(self):
        s=build_v2_2_4_status()
        self.assertTrue(s["confidence_grid_search"])
        self.assertTrue(s["reward_risk_grid_search"])
        self.assertTrue(s["regime_specific_candidates"])
        self.assertTrue(s["champion_policy_registry"])
        self.assertFalse(s["promotion_enabled"])
        self.assertFalse(s["challenger_execution_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
