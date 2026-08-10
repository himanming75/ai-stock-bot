from pathlib import Path
from datetime import datetime,timezone,timedelta
import csv,json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.training_dataset_builder_v2_2_9 import TrainingDatasetBuilderV229
from ai_engine_v2.training_dataset_builder_status_v2_2_9 import build_v2_2_9_status


def setup_policy(root,min_dates=12,min_rows=1):
    p=Path(root)/"release"/"ai_trading_engine_v2_2_9_training_dataset_builder"/"config"
    p.mkdir(parents=True,exist_ok=True)
    (p/"training_dataset_policy.json").write_text(json.dumps({
        "horizons_minutes":[5,15,30,60],
        "feature_columns":[
            "return_1m_pct","return_5m_pct","return_15m_pct",
            "close_vs_sma20_pct","rolling_volatility_20",
            "volume_ratio_20","range_pct","rsi_14"
        ],
        "metadata_columns":["timestamp","market_date","symbol","feed"],
        "train_fraction":.70,"validation_fraction":.15,"test_fraction":.15,
        "embargo_trading_days":1,
        "require_all_features":True,
        "min_unique_market_dates":min_dates,
        "min_rows_for_ready":min_rows,
        "direction_deadband_pct":.05
    }),encoding="utf-8")


def row(day,minute=0,symbol="AAPL",ret=.2):
    ts=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=day,hours=14,minutes=30+minute)
    features={
        "return_1m_pct":.1,"return_5m_pct":.2,"return_15m_pct":.3,
        "close_vs_sma20_pct":.1,"rolling_volatility_20":.2,
        "volume_ratio_20":1.1,"range_pct":.3,"rsi_14":55
    }
    labels={}
    for h in (5,15,30,60):
        labels[f"{h}m"]={
            "forward_return_pct":ret,
            "mfe_pct":abs(ret)+.1,
            "mae_pct":-.1,
            "target_timestamp":(
                ts+timedelta(minutes=h)
            ).isoformat().replace("+00:00","Z"),
            "direction":"UP"
        }
    return {
        "symbol":symbol,
        "timestamp":ts.isoformat().replace("+00:00","Z"),
        "feed":"iex",
        "features":features,
        "forward_labels":labels,
    }


def write_source(c,rows):
    c.source.parent.mkdir(parents=True,exist_ok=True)
    with c.source.open("w",encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r)+"\n")


class Tests(unittest.TestCase):
    def test_waiting_when_source_missing(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td)
            r=TrainingDatasetBuilderV229(td).build()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_2_8_1_TRAINING_FORWARD_LABELS"
            )
            self.assertFalse(r["dataset_ready"])

    def test_waiting_for_dates(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td,min_dates=12)
            c=TrainingDatasetBuilderV229(td)
            write_source(c,[row(i) for i in range(5)])
            r=c.build()
            self.assertEqual(r["status"],"WAITING_FOR_MORE_MARKET_DATES")

    def test_chronological_split_and_embargo(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td,min_dates=12,min_rows=1)
            c=TrainingDatasetBuilderV229(td)
            rows=[]
            for d in range(20):
                rows.append(row(d,0,"AAPL",.2))
                rows.append(row(d,1,"MSFT",-.2))
            write_source(c,rows)
            r=c.build()
            self.assertEqual(r["status"],"PASS_TRAINING_DATASET_BUILD")
            lg=r["leakage_guard"]
            sd=r["split_dates"]
            self.assertTrue(lg["chronological_order_verified"])
            self.assertEqual(lg["embargo_trading_days"],1)
            self.assertEqual(len(sd["embargo_1"]),1)
            self.assertEqual(len(sd["embargo_2"]),1)
            self.assertFalse(lg["random_shuffle_before_split"])
            self.assertTrue(lg["future_target_columns_excluded_from_features"])
            self.assertLess(max(sd["train"]),min(sd["embargo_1"]))
            self.assertLess(max(sd["embargo_1"]),min(sd["validation"]))
            self.assertLess(max(sd["validation"]),min(sd["embargo_2"]))
            self.assertLess(max(sd["embargo_2"]),min(sd["test"]))

    def test_no_target_in_feature_columns(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td,min_dates=12,min_rows=1)
            c=TrainingDatasetBuilderV229(td)
            write_source(c,[row(d) for d in range(20)])
            r=c.build()
            path=Path(td)/r["artifacts"]["15m"]["train"]["path"]
            with path.open(newline="",encoding="utf-8") as f:
                header=next(csv.reader(f))
            feature_names=set(r["features"])
            self.assertNotIn("target_return_pct",feature_names)
            self.assertIn("target_return_pct",header)
            self.assertIn("target_direction",header)

    def test_deadband_direction(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td,min_dates=12,min_rows=1)
            c=TrainingDatasetBuilderV229(td)
            rows=[]
            for d in range(20):
                rows.append(row(d,ret=.01))
            write_source(c,rows)
            r=c.build()
            cc=r["artifacts"]["5m"]["train"]["class_counts"]
            self.assertGreater(cc.get("FLAT",0),0)

    def test_missing_features_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            setup_policy(td,min_dates=12,min_rows=1)
            c=TrainingDatasetBuilderV229(td)
            rows=[row(d) for d in range(20)]
            rows[0]["features"]["rsi_14"]=None
            write_source(c,rows)
            r=c.build()
            self.assertGreater(
                r["skip_counts"].get("5m_MISSING_FEATURE",0),0
            )

    def test_status_contract(self):
        s=build_v2_2_9_status()
        self.assertTrue(s["streaming_two_pass_builder"])
        self.assertTrue(s["chronological_market_date_split"])
        self.assertTrue(s["train_validation_test"])
        self.assertEqual(s["embargo_trading_days"],1)
        self.assertFalse(s["random_shuffle_before_split"])
        self.assertTrue(s["future_target_leakage_guard"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
