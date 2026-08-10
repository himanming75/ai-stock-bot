from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.performance_segmentation_feature_attribution_v2_2_3 import (
    PerformanceSegmentationFeatureAttributionV223,
    confidence_bin,
    reward_risk_bin,
)
from ai_engine_v2.performance_segmentation_feature_attribution_status_v2_2_3 import (
    build_v2_2_3_status,
)


def outcome(
    rid,
    *,
    symbol="AAPL",
    label="WIN",
    pnl="2.0",
    ret="0.2",
    confidence=0.82,
    rr=1.4,
    alignment=0.82,
    quality=0.72,
    regime="WEAK_BULL",
    structure="NORMAL",
    exit_reason="TAKE_PROFIT",
):
    return {
        "status":"LABELED_BOUND_PAPER_OUTCOME",
        "round_trip_id":rid,
        "symbol":symbol,
        "outcome":{
            "outcome_label":label,
            "gross_pnl_from_fills":pnl,
            "return_pct_from_fills":ret,
            "holding_seconds":600,
            "exit_reason":exit_reason,
        },
        "feature_binding":{
            "action":"BUY",
            "market_regime":regime,
            "dominant_structure":structure,
            "reward_risk":rr,
            "trend_alignment":alignment,
            "shadow_quality_score":quality,
            "probability":0.8,
            "feature_lag_seconds":60,
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
    path=p/"labeled_outcomes.jsonl"
    path.write_text(
        "".join(json.dumps(r)+"\n" for r in rows),
        encoding="utf-8",
    )


class Tests(unittest.TestCase):
    def test_waiting_no_outcomes(self):
        with tempfile.TemporaryDirectory() as td:
            r=PerformanceSegmentationFeatureAttributionV223(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
            )
            self.assertFalse(r["calibration_ready"])
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_metrics_and_segments(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[
                outcome("1"),
                outcome(
                    "2",label="LOSS",pnl="-1.0",ret="-0.1",
                    confidence=0.78,rr=1.1,regime="RANGE",
                    exit_reason="STOP_LOSS",
                ),
                outcome("3",symbol="MSFT",pnl="3.0",ret="0.3"),
            ])
            c=PerformanceSegmentationFeatureAttributionV223(td)
            r=c.build()
            self.assertEqual(
                r["status"],
                "PASS_PERFORMANCE_SEGMENTATION_FEATURE_ATTRIBUTION",
            )
            self.assertEqual(r["overall"]["trades"],3)
            self.assertEqual(r["overall"]["wins"],2)
            self.assertEqual(r["overall"]["losses"],1)
            self.assertAlmostEqual(
                r["overall"]["gross_pnl_before_fees"],4.0
            )
            self.assertAlmostEqual(
                r["overall"]["profit_factor"],5.0
            )
            self.assertIn("AAPL",r["by_symbol"])
            self.assertIn("MSFT",r["by_symbol"])
            self.assertIn("WEAK_BULL",r["by_market_regime"])
            self.assertIn("RANGE",r["by_market_regime"])
            self.assertFalse(r["calibration_ready"])
            self.assertFalse(r["execution_selector_modified"])

    def test_actionable_at_five_samples(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[
                outcome(str(i),confidence=0.82,rr=1.4)
                for i in range(5)
            ]
            write_source(td,rows)
            r=PerformanceSegmentationFeatureAttributionV223(td).build()
            self.assertTrue(r["calibration_ready"])
            self.assertTrue(
                r["by_confidence_bin"]["0.80-0.85"][
                    "actionable_sample"
                ]
            )
            self.assertIn(
                "0.80-0.85",
                r["actionable_rankings"]["confidence_bins"],
            )

    def test_bins(self):
        self.assertEqual(confidence_bin(0.74),"<0.75")
        self.assertEqual(confidence_bin(0.75),"0.75-0.80")
        self.assertEqual(confidence_bin(0.90),"0.90+")
        self.assertEqual(reward_risk_bin(0.9),"<1.00")
        self.assertEqual(reward_risk_bin(1.25),"1.25-1.50")
        self.assertEqual(reward_risk_bin(2.2),"2.00+")

    def test_markdown_report_created(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[outcome("1")])
            c=PerformanceSegmentationFeatureAttributionV223(td)
            c.build()
            self.assertTrue(c.json_report.exists())
            self.assertTrue(c.md_report.exists())
            text=c.md_report.read_text(encoding="utf-8")
            self.assertIn("Market Regime",text)
            self.assertIn("Execution selector modified: FALSE",text)

    def test_status_contract(self):
        s=build_v2_2_3_status()
        self.assertTrue(s["v2_2_2_labeled_outcomes_reused"])
        self.assertTrue(s["market_regime_segmentation"])
        self.assertTrue(s["confidence_segmentation"])
        self.assertTrue(s["profit_factor"])
        self.assertEqual(s["minimum_actionable_sample"],5)
        self.assertFalse(s["threshold_change_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
