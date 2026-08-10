from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.signal_scoring_feature_snapshot_v2_2_1 import (
    SignalScoringFeatureSnapshotV221,
)
from ai_engine_v2.signal_scoring_feature_snapshot_status_v2_2_1 import (
    build_v2_2_1_status,
)


def analysis(symbol,action,conf,rr,consensus=0.2):
    tfs=[]
    for tf in ("1m","3m","5m","15m","30m","1h","1d"):
        tfs.append({
            "timeframe":tf,
            "signal":action,
            "directional_score":consensus,
            "trend_score":0.5,
            "momentum_score":0.4,
            "regime":"WEAK_BULL",
            "structure":"NORMAL",
            "probability":0.8,
            "expected_return":0.02,
            "expected_risk":0.01,
            "reward_risk":rr,
            "features":{
                "close":100,
                "ema_fast":101,
                "ema_slow":99,
                "momentum":0.01,
                "rsi":60,
                "volume_ratio":1.2,
                "atr_percent":0.01,
                "gap_percent":0,
                "close_vs_range":0.7,
                "follow_through":0.01,
            },
        })
    return {
        "symbol":symbol,
        "action":action,
        "consensus_score":consensus,
        "timeframe_consensus":{
            "buy_weight":0.8,
            "sell_weight":0,
            "hold_weight":0.2,
            "alignment":0.8,
            "disagreement":0.2,
        },
        "trend_alignment":0.8,
        "market_regime_2":"WEAK_BULL",
        "dominant_structure":"NORMAL",
        "probability":0.8,
        "expected_return":0.02,
        "expected_risk":0.01,
        "reward_risk":rr,
        "confidence_calibration":{
            "raw_confidence":conf,
            "calibrated_confidence":conf,
        },
        "timeframes":tfs,
        "execution_mode":"ANALYSIS_ONLY",
    }


def write_source(root,analyses):
    p=Path(root)/"runtime"/"real_market_multitimeframe_shadow"
    p.mkdir(parents=True,exist_ok=True)
    src=p/"latest_real_market_shadow.json"
    src.write_text(json.dumps({
        "generated_at_utc":"2026-08-10T16:00:00+00:00",
        "source_dataset":"TEST",
        "canonical_engine":
            "multi_timeframe_ai.engine.analyze_symbol",
        "canonical_selector":
            "paper_autonomous_execution.signals.select_candidate",
        "thresholds":{
            "min_confidence":0.75,
            "min_reward_risk":1.0,
        },
        "mode":"SHADOW_ANALYSIS_ONLY",
        "analyses":analyses,
    }),encoding="utf-8")
    return src


class Tests(unittest.TestCase):
    def test_eligible_and_block_reasons(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[
                analysis("AAPL","BUY",0.82,1.4),
                analysis("MSFT","HOLD",0.70,0.7,0.02),
            ])
            c=SignalScoringFeatureSnapshotV221(td)
            r=c.build()
            self.assertEqual(
                r["status"],
                "PASS_AI_SIGNAL_SCORING_FEATURE_SNAPSHOT",
            )
            self.assertEqual(r["snapshot_rows"],2)
            self.assertEqual(r["current_selector_eligible_count"],1)
            latest=json.loads(c.latest.read_text())
            by={x["symbol"]:x for x in latest["symbol_rows"]}
            self.assertTrue(
                by["AAPL"]["selector_explanation"][
                    "current_selector_eligible"
                ]
            )
            reasons=by["MSFT"]["selector_explanation"][
                "current_selector_block_reasons"
            ]
            self.assertIn("ACTION_NOT_BUY_OR_SELL",reasons)
            self.assertIn("CONFIDENCE_BELOW_CURRENT_SELECTOR",reasons)
            self.assertIn("REWARD_RISK_BELOW_CURRENT_SELECTOR",reasons)

    def test_dedup_same_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[analysis("AAPL","BUY",0.82,1.4)])
            c=SignalScoringFeatureSnapshotV221(td)
            a=c.build()
            b=c.build()
            self.assertEqual(a["new_ledger_rows"],1)
            self.assertEqual(b["new_ledger_rows"],0)
            self.assertTrue(b["duplicate_snapshot"])

    def test_missing_source_waits(self):
        with tempfile.TemporaryDirectory() as td:
            r=SignalScoringFeatureSnapshotV221(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_CANONICAL_REAL_MARKET_SHADOW",
            )
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_shadow_score_never_enables_execution(self):
        with tempfile.TemporaryDirectory() as td:
            write_source(td,[analysis("AAPL","BUY",0.90,1.8)])
            c=SignalScoringFeatureSnapshotV221(td)
            c.build()
            latest=json.loads(c.latest.read_text())
            self.assertTrue(latest["shadow_quality_score_only"])
            self.assertFalse(latest["execution_selector_modified"])
            self.assertFalse(
                latest["symbol_rows"][0][
                    "quality_score_execution_enabled"
                ]
            )

    def test_status_contract(self):
        s=build_v2_2_1_status()
        self.assertTrue(s["existing_canonical_engine_reused"])
        self.assertTrue(s["existing_canonical_selector_reused"])
        self.assertTrue(s["selector_block_reason_capture"])
        self.assertFalse(s["quality_score_execution_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
