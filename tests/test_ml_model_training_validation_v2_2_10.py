from pathlib import Path
import csv,importlib.util,json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.ml_model_training_validation_v2_2_10 import (
    MLModelTrainingValidationV2210,
    ml_dependencies_available,
)
from ai_engine_v2.ml_model_training_validation_status_v2_2_10 import (
    build_v2_2_10_status,
)


FEATURES=[
    "return_1m_pct","return_5m_pct","return_15m_pct",
    "close_vs_sma20_pct","rolling_volatility_20",
    "volume_ratio_20","range_pct","rsi_14"
]


def setup(root):
    root=Path(root)
    cfg=root/"release"/"ai_trading_engine_v2_2_10_ml_model_training_validation"/"config"
    cfg.mkdir(parents=True,exist_ok=True)
    (cfg/"ml_training_policy.json").write_text(json.dumps({
        "horizons_minutes":[5],
        "feature_columns":FEATURES,
        "target_column":"target_direction",
        "class_labels":["DOWN","FLAT","UP"],
        "candidate_models":["dummy_prior","logistic_balanced","hist_gradient_boosting"],
        "selection_metric":"mean_macro_f1_balanced_accuracy",
        "minimum_validation_improvement_over_dummy":0.0,
        "max_train_rows_per_horizon":1000,
        "max_walk_forward_train_rows":500,
        "max_walk_forward_eval_rows":200,
        "walk_forward_folds":2,
        "walk_forward_embargo_market_dates":1,
        "random_seed":42,
        "test_set_used_for_selection":False,
        "automatic_promotion":False,
        "execution_selector_modified":False
    }),encoding="utf-8")
    dr=root/"runtime"/"ai_training_dataset_builder_v2_2_9"/"datasets"
    dr.mkdir(parents=True,exist_ok=True)
    manifest=root/"runtime"/"ai_training_dataset_builder_v2_2_9"/"dataset_manifest.json"
    manifest.write_text(json.dumps({
        "dataset_ready":True,
        "source_rows":100,
        "source_unique_market_dates":20
    }),encoding="utf-8")
    return root,dr


def write_csv(path,n,start_day=1):
    fields=["timestamp","market_date","symbol","feed"]+FEATURES+[
        "target_horizon_min","target_return_pct",
        "target_mfe_pct","target_mae_pct",
        "target_direction","target_timestamp"
    ]
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for i in range(n):
            day=start_day+(i//10)
            signal=(i%10)-5
            if signal>=2:
                target="UP"
            elif signal<=-2:
                target="DOWN"
            else:
                target="FLAT"
            feat={
                "return_1m_pct":signal*.1,
                "return_5m_pct":signal*.2,
                "return_15m_pct":signal*.3,
                "close_vs_sma20_pct":signal*.1,
                "rolling_volatility_20":.2+abs(signal)*.01,
                "volume_ratio_20":1+signal*.02,
                "range_pct":.3+abs(signal)*.01,
                "rsi_14":50+signal*4,
            }
            w.writerow({
                "timestamp":f"2026-01-{day:02d}T15:00:00Z",
                "market_date":f"2026-01-{day:02d}",
                "symbol":"AAPL","feed":"iex",
                **feat,
                "target_horizon_min":5,
                "target_return_pct":signal*.1,
                "target_mfe_pct":abs(signal)*.1+.1,
                "target_mae_pct":-.1,
                "target_direction":target,
                "target_timestamp":f"2026-01-{day:02d}T15:05:00Z",
            })


class Tests(unittest.TestCase):
    def test_preflight_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root,_=setup(td)
            c=MLModelTrainingValidationV2210(root)
            r=c.preflight()
            self.assertEqual(r["status"],"WAITING_FOR_V2_2_9_DATASETS")
            self.assertFalse(r["training_ready"])

    def test_policy_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root,_=setup(td)
            c=MLModelTrainingValidationV2210(root)
            p=json.loads(c.policy_path.read_text())
            p["test_set_used_for_selection"]=True
            c.policy_path.write_text(json.dumps(p))
            with self.assertRaises(RuntimeError):
                c.policy()

    def test_cap_rows_is_bounded(self):
        if not ml_dependencies_available():
            self.skipTest("ML dependencies unavailable")
        import numpy as np
        X=np.arange(8000,dtype=float).reshape(1000,8)
        y=np.asarray(["UP"]*1000,dtype=object)
        d=np.asarray(["2026-01-01"]*1000,dtype=object)
        s=np.asarray(["AAPL"]*1000,dtype=object)
        X2,y2,d2,s2,capped=MLModelTrainingValidationV2210._cap_rows(
            X,y,d,s,100
        )
        self.assertTrue(capped)
        self.assertEqual(len(y2),100)
        self.assertEqual(X2.shape,(100,8))

    def test_metrics_contract(self):
        if not ml_dependencies_available():
            self.skipTest("ML dependencies unavailable")
        y=["UP","DOWN","FLAT","UP"]
        m=MLModelTrainingValidationV2210._metrics(
            y,y,["DOWN","FLAT","UP"]
        )
        self.assertEqual(m["accuracy"],1.0)
        self.assertEqual(m["macro_f1"],1.0)
        self.assertEqual(m["selection_score"],1.0)

    def test_small_end_to_end_training(self):
        if not ml_dependencies_available():
            self.skipTest("ML dependencies unavailable")
        with tempfile.TemporaryDirectory() as td:
            root,dr=setup(td)
            write_csv(dr/"train_5m.csv",180,1)
            write_csv(dr/"validation_5m.csv",60,19)
            write_csv(dr/"test_5m.csv",60,25)
            c=MLModelTrainingValidationV2210(root)
            r=c.train_all()
            self.assertEqual(r["status"],"PASS_ML_MODEL_TRAINING_VALIDATION")
            h=r["horizons"]["5m"]
            self.assertFalse(h["test_used_for_selection"])
            self.assertTrue(h["test_evaluated_after_selection"])
            self.assertTrue((root/h["model_path"]).exists())
            self.assertFalse(r["automatic_promotion"])
            self.assertFalse(r["execution_selector_modified"])

    def test_status_contract(self):
        s=build_v2_2_10_status()
        self.assertTrue(s["isolated_ml_venv"])
        self.assertTrue(s["validation_only_model_selection"])
        self.assertFalse(s["test_used_for_selection"])
        self.assertTrue(s["test_evaluated_after_selection"])
        self.assertTrue(s["bounded_walk_forward"])
        self.assertEqual(s["walk_forward_embargo_market_dates"],1)
        self.assertFalse(s["automatic_promotion"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
