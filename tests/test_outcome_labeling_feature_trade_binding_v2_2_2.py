from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.outcome_labeling_feature_trade_binding_v2_2_2 import (
    OutcomeLabelingFeatureTradeBindingV222,
)
from ai_engine_v2.outcome_labeling_feature_trade_binding_status_v2_2_2 import (
    build_v2_2_2_status,
)


def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        "".join(json.dumps(r)+"\n" for r in rows),
        encoding="utf-8",
    )


def feature_snapshot(ts,symbol="AAPL",quality=0.7):
    return {
        "snapshot_id":f"snap-{ts}",
        "observed_at_utc":ts,
        "source_snapshot_sha256":"source-sha",
        "symbol_rows":[{
            "symbol":symbol,
            "action":"BUY",
            "quality_score_shadow":quality,
            "consensus_score":0.3,
            "trend_alignment":0.8,
            "market_regime":"WEAK_BULL",
            "dominant_structure":"NORMAL",
            "probability":0.8,
            "expected_return":0.02,
            "expected_risk":0.01,
            "reward_risk":1.4,
            "confidence_calibration":{
                "calibrated_confidence":0.82
            },
            "timeframe_consensus":{"alignment":0.8},
            "selector_explanation":{
                "current_selector_eligible":True,
                "current_selector_block_reasons":[],
            },
            "timeframes":[{"timeframe":"1m","signal":"BUY"}],
            "canonical_analysis_sha256":"analysis-sha",
        }],
    }


def trade(
    rid="rt1",
    symbol="AAPL",
    entry_time="2026-08-10T16:05:00+00:00",
    pnl="2.50",
    ret="0.25",
):
    return {
        "stage":"BROKER_INTEGRATION_V2_1_27_COMPLETED_ROUND_TRIP",
        "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
        "round_trip_id":rid,
        "evidence_key":"ev1",
        "symbol":symbol,
        "entry":{
            "filled_at":entry_time,
            "filled_avg_price":"100",
        },
        "exit":{
            "filled_at":"2026-08-10T16:15:00+00:00",
            "filled_avg_price":"100.25",
            "reason":"TAKE_PROFIT",
        },
        "holding_seconds":600,
        "gross_pnl_from_fills":pnl,
        "return_pct_from_fills":ret,
        "fees_included":False,
        "pnl_semantics":"FILL_BASED_GROSS_PNL_BEFORE_FEES",
    }


class Tests(unittest.TestCase):
    def paths(self,td):
        root=Path(td)
        fl=root/"runtime"/"ai_signal_scoring_feature_snapshot_v2_2_1"/"feature_snapshot_ledger.jsonl"
        tl=root/"runtime"/"final_round_trip_ledger_v2_1_27"/"completed_round_trips.jsonl"
        return root,fl,tl

    def test_win_binds_to_closest_pre_entry_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,tl=self.paths(td)
            write_jsonl(fl,[
                feature_snapshot("2026-08-10T15:40:00+00:00",quality=0.4),
                feature_snapshot("2026-08-10T16:04:00+00:00",quality=0.8),
            ])
            write_jsonl(tl,[trade()])
            c=OutcomeLabelingFeatureTradeBindingV222(root)
            r=c.build()
            self.assertEqual(r["new_labeled_outcomes"],1)
            row=json.loads(c.latest.read_text())
            self.assertEqual(row["outcome"]["outcome_label"],"WIN")
            self.assertEqual(
                row["feature_binding"]["feature_lag_seconds"],60.0
            )
            self.assertEqual(
                row["feature_binding"]["shadow_quality_score"],0.8
            )
            self.assertFalse(row["pnl_recomputed"])

    def test_loss_label(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,tl=self.paths(td)
            write_jsonl(fl,[
                feature_snapshot("2026-08-10T16:04:00+00:00")
            ])
            write_jsonl(tl,[
                trade(pnl="-1.50",ret="-0.15")
            ])
            c=OutcomeLabelingFeatureTradeBindingV222(root)
            c.build()
            row=json.loads(c.latest.read_text())
            self.assertEqual(row["outcome"]["outcome_label"],"LOSS")

    def test_future_snapshot_is_not_used(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,tl=self.paths(td)
            write_jsonl(fl,[
                feature_snapshot("2026-08-10T16:06:00+00:00")
            ])
            write_jsonl(tl,[trade()])
            c=OutcomeLabelingFeatureTradeBindingV222(root)
            r=c.build()
            self.assertEqual(r["new_labeled_outcomes"],0)
            self.assertEqual(r["new_unbound_outcomes"],1)
            rows=c._read_jsonl(c.unbound_ledger)
            self.assertEqual(
                rows[0]["binding_error"],
                "NO_PRE_ENTRY_FEATURE_SNAPSHOT",
            )

    def test_stale_snapshot_is_unbound(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,tl=self.paths(td)
            write_jsonl(fl,[
                feature_snapshot("2026-08-10T15:00:00+00:00")
            ])
            write_jsonl(tl,[trade()])
            c=OutcomeLabelingFeatureTradeBindingV222(root)
            r=c.build()
            self.assertEqual(r["new_unbound_outcomes"],1)
            rows=c._read_jsonl(c.unbound_ledger)
            self.assertEqual(
                rows[0]["binding_error"],
                "FEATURE_SNAPSHOT_TOO_OLD",
            )

    def test_dedup_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root,fl,tl=self.paths(td)
            write_jsonl(fl,[
                feature_snapshot("2026-08-10T16:04:00+00:00")
            ])
            write_jsonl(tl,[trade()])
            c=OutcomeLabelingFeatureTradeBindingV222(root)
            a=c.build()
            b=c.build()
            self.assertEqual(a["new_labeled_outcomes"],1)
            self.assertEqual(b["new_labeled_outcomes"],0)
            self.assertEqual(b["duplicate_round_trips"],1)

    def test_waiting_without_completed_trades(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r=OutcomeLabelingFeatureTradeBindingV222(root).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_1_27_COMPLETED_ROUND_TRIPS",
            )
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_status_contract(self):
        s=build_v2_2_2_status()
        self.assertTrue(s["v2_2_1_feature_ledger_reused"])
        self.assertTrue(s["v2_1_27_completed_trade_ledger_reused"])
        self.assertTrue(s["actual_fill_outcomes_used_as_labels"])
        self.assertFalse(s["pnl_recomputed"])
        self.assertEqual(s["max_feature_lag_seconds"],1800)
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
