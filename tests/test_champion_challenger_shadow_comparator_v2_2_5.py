from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.champion_challenger_shadow_comparator_v2_2_5 import (
    ChampionChallengerShadowComparatorV225,
)
from ai_engine_v2.champion_challenger_shadow_comparator_status_v2_2_5 import (
    build_v2_2_5_status,
)


def symbol_row(symbol,action,confidence,rr,quality=.7):
    reasons=[]
    if action not in {"BUY","SELL"}:
        reasons.append("ACTION_NOT_BUY_OR_SELL")
    if confidence<.75:
        reasons.append("CONFIDENCE_BELOW_CURRENT_SELECTOR")
    if rr<1.0:
        reasons.append("REWARD_RISK_BELOW_CURRENT_SELECTOR")
    return {
        "symbol":symbol,
        "action":action,
        "quality_score_shadow":quality,
        "market_regime":"WEAK_BULL",
        "reward_risk":rr,
        "confidence_calibration":{
            "calibrated_confidence":confidence
        },
        "selector_explanation":{
            "current_selector_eligible":len(reasons)==0,
            "current_selector_block_reasons":reasons,
        },
        "canonical_analysis_sha256":f"sha-{symbol}",
    }


def write_snapshot(root,rows):
    p=(
        Path(root)/"runtime"/
        "ai_signal_scoring_feature_snapshot_v2_2_1"
    )
    p.mkdir(parents=True,exist_ok=True)
    (p/"latest_feature_snapshot.json").write_text(
        json.dumps({
            "snapshot_id":"snap1",
            "observed_at_utc":"2026-08-10T16:00:00+00:00",
            "source_snapshot_sha256":"source1",
            "symbol_rows":rows,
        }),
        encoding="utf-8",
    )


def write_registry(root,challengers):
    p=(
        Path(root)/"runtime"/
        "ai_threshold_calibration_challenger_policy_v2_2_4"
    )
    p.mkdir(parents=True,exist_ok=True)
    (p/"challenger_policy_registry.json").write_text(
        json.dumps({
            "champion":{
                "policy_id":"CHAMPION",
                "min_confidence":.75,
                "min_reward_risk":1.0,
                "execution_enabled":True,
            },
            "challengers":challengers,
            "registry_sha256":"registry1",
            "promotion_enabled":False,
            "challenger_execution_enabled":False,
        }),
        encoding="utf-8",
    )


class Tests(unittest.TestCase):
    def test_waiting_no_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            r=ChampionChallengerShadowComparatorV225(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_1_FEATURE_SNAPSHOT",
            )
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_seed_fallback_and_classification(self):
        with tempfile.TemporaryDirectory() as td:
            write_snapshot(td,[
                symbol_row("AAPL","BUY",.76,1.05,.8),
                symbol_row("MSFT","BUY",.72,1.20,.7),
                symbol_row("SPY","HOLD",.90,2.0,.9),
            ])
            c=ChampionChallengerShadowComparatorV225(td)
            r=c.build()
            self.assertEqual(r["challengers_compared"],2)
            self.assertIn("SEED_FALLBACK",r["policy_source"])
            self.assertGreater(r["comparison_rows"],0)
            self.assertFalse(r["challenger_execution_enabled"])
            latest=json.loads(c.latest.read_text())
            classes=[
                x["classification"]
                for comp in latest["comparisons"]
                for x in comp["symbol_comparisons"]
            ]
            self.assertIn("CHAMPION_ONLY",classes)
            self.assertIn("CHALLENGER_ONLY",classes)
            self.assertIn("NEITHER",classes)

    def test_calibrated_registry_preferred(self):
        with tempfile.TemporaryDirectory() as td:
            write_snapshot(td,[
                symbol_row("AAPL","BUY",.82,1.4,.8)
            ])
            write_registry(td,[{
                "policy_id":"CHALLENGER_GLOBAL_1",
                "min_confidence":.80,
                "min_reward_risk":1.25,
                "execution_enabled":False,
            }])
            c=ChampionChallengerShadowComparatorV225(td)
            r=c.build()
            self.assertEqual(
                r["policy_source"],
                "V2_2_4_CALIBRATED_REGISTRY",
            )
            self.assertEqual(r["challengers_compared"],1)
            latest=json.loads(c.latest.read_text())
            self.assertEqual(
                latest["comparisons"][0]["challenger_policy"]["policy_id"],
                "CHALLENGER_GLOBAL_1",
            )

    def test_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            write_snapshot(td,[
                symbol_row("AAPL","BUY",.82,1.4)
            ])
            c=ChampionChallengerShadowComparatorV225(td)
            a=c.build()
            b=c.build()
            self.assertEqual(a["new_ledger_rows"],1)
            self.assertEqual(b["new_ledger_rows"],0)
            self.assertTrue(b["duplicate_comparison"])

    def test_best_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            write_snapshot(td,[
                symbol_row("AAPL","BUY",.82,1.4,.60),
                symbol_row("MSFT","BUY",.83,1.5,.85),
            ])
            c=ChampionChallengerShadowComparatorV225(td)
            c.build()
            latest=json.loads(c.latest.read_text())
            self.assertEqual(
                latest["comparisons"][0][
                    "champion_best_shadow_candidate"
                ]["symbol"],
                "MSFT",
            )

    def test_status_contract(self):
        s=build_v2_2_5_status()
        self.assertTrue(s["same_snapshot_comparison"])
        self.assertTrue(s["seed_fallback_when_registry_empty"])
        self.assertTrue(s["challenger_only_classification"])
        self.assertTrue(s["comparison_jsonl_ledger"])
        self.assertFalse(s["challenger_execution_enabled"])
        self.assertFalse(s["promotion_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
