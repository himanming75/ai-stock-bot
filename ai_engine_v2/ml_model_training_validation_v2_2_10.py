from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(
        json.dumps(value,indent=2,sort_keys=True,default=str),
        encoding="utf-8",
    )
    os.replace(tmp,path)


def _sha_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ml_dependencies_available():
    return all(
        importlib.util.find_spec(name) is not None
        for name in ("numpy","sklearn","joblib")
    )


class MLModelTrainingValidationV2210:
    """
    Offline ML trainer.

    Validation chooses the candidate. The test set is loaded/evaluated only
    after candidate selection. No broker/order/execution code is present.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.policy_path=(
            self.root/"release"/
            "ai_trading_engine_v2_2_10_ml_model_training_validation"/
            "config"/"ml_training_policy.json"
        )
        self.dataset_root=(
            self.root/"runtime"/
            "ai_training_dataset_builder_v2_2_9"/"datasets"
        )
        self.dataset_manifest=(
            self.root/"runtime"/
            "ai_training_dataset_builder_v2_2_9"/
            "dataset_manifest.json"
        )
        self.runtime=(
            self.root/"runtime"/
            "ai_ml_model_training_validation_v2_2_10"
        )
        self.models_dir=self.runtime/"models"
        self.reports_dir=self.runtime/"reports"
        self.latest=self.runtime/"latest_training_report.json"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.models_dir.mkdir(parents=True,exist_ok=True)
        self.reports_dir.mkdir(parents=True,exist_ok=True)

    def policy(self):
        p=json.loads(self.policy_path.read_text(encoding="utf-8-sig"))
        if p.get("test_set_used_for_selection") is not False:
            raise RuntimeError("TEST_SELECTION_MUST_BE_DISABLED")
        if p.get("automatic_promotion") is not False:
            raise RuntimeError("AUTOMATIC_PROMOTION_MUST_BE_DISABLED")
        if p.get("execution_selector_modified") is not False:
            raise RuntimeError("EXECUTION_SELECTOR_MUST_REMAIN_UNMODIFIED")
        if int(p["walk_forward_embargo_market_dates"])<1:
            raise RuntimeError("WALK_FORWARD_EMBARGO_REQUIRED")
        return p

    def _dataset_paths(self,h):
        return {
            s:self.dataset_root/f"{s}_{int(h)}m.csv"
            for s in ("train","validation","test")
        }

    def preflight(self):
        p=self.policy()
        missing=[]
        if not self.dataset_manifest.exists():
            missing.append(str(self.dataset_manifest))
        for h in p["horizons_minutes"]:
            for path in self._dataset_paths(h).values():
                if not path.exists():
                    missing.append(str(path))
        if missing:
            return {
                "status":"WAITING_FOR_V2_2_9_DATASETS",
                "missing_count":len(missing),
                "missing":missing[:10],
                "ml_dependencies_available":ml_dependencies_available(),
                "training_ready":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }

        manifest=json.loads(
            self.dataset_manifest.read_text(encoding="utf-8")
        )
        if manifest.get("dataset_ready") is not True:
            return {
                "status":"BLOCKED_V2_2_9_DATASET_NOT_READY",
                "training_ready":False,
                "ml_dependencies_available":ml_dependencies_available(),
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }

        return {
            "status":"PASS_ML_TRAINING_PREFLIGHT",
            "dataset_ready":True,
            "ml_dependencies_available":ml_dependencies_available(),
            "training_ready":ml_dependencies_available(),
            "source_rows":manifest.get("source_rows"),
            "source_unique_market_dates":
                manifest.get("source_unique_market_dates"),
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }

    @staticmethod
    def _import_ml():
        if not ml_dependencies_available():
            raise RuntimeError("ML_DEPENDENCIES_MISSING_USE_VENV_ML_SETUP")
        import numpy as np
        import joblib
        from sklearn.dummy import DummyClassifier
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import (
            accuracy_score,
            balanced_accuracy_score,
            confusion_matrix,
            f1_score,
        )
        from sklearn.utils.class_weight import compute_sample_weight
        return {
            "np":np,
            "joblib":joblib,
            "DummyClassifier":DummyClassifier,
            "HistGradientBoostingClassifier":HistGradientBoostingClassifier,
            "LogisticRegression":LogisticRegression,
            "Pipeline":Pipeline,
            "StandardScaler":StandardScaler,
            "accuracy_score":accuracy_score,
            "balanced_accuracy_score":balanced_accuracy_score,
            "confusion_matrix":confusion_matrix,
            "f1_score":f1_score,
            "compute_sample_weight":compute_sample_weight,
        }

    @staticmethod
    def _read_csv(path,feature_columns,target_column):
        ml=MLModelTrainingValidationV2210._import_ml()
        np=ml["np"]
        features=[]
        targets=[]
        dates=[]
        symbols=[]
        with path.open("r",encoding="utf-8",newline="") as f:
            reader=csv.DictReader(f)
            for row in reader:
                try:
                    x=[float(row[c]) for c in feature_columns]
                except (KeyError,TypeError,ValueError):
                    continue
                if not all(math.isfinite(v) for v in x):
                    continue
                y=row.get(target_column)
                if not y:
                    continue
                features.append(x)
                targets.append(y)
                dates.append(row.get("market_date") or "")
                symbols.append(row.get("symbol") or "")
        X=np.asarray(features,dtype=np.float32)
        y=np.asarray(targets,dtype=object)
        d=np.asarray(dates,dtype=object)
        s=np.asarray(symbols,dtype=object)
        return X,y,d,s

    @staticmethod
    def _cap_rows(X,y,dates,symbols,max_rows):
        n=len(y)
        if max_rows<=0 or n<=max_rows:
            return X,y,dates,symbols,False
        ml=MLModelTrainingValidationV2210._import_ml()
        np=ml["np"]
        # Deterministic evenly-spaced sample preserves the full time span.
        idx=np.linspace(0,n-1,num=int(max_rows),dtype=int)
        return X[idx],y[idx],dates[idx],symbols[idx],True

    @staticmethod
    def _candidate(name,p):
        ml=MLModelTrainingValidationV2210._import_ml()
        seed=int(p["random_seed"])
        if name=="dummy_prior":
            return ml["DummyClassifier"](strategy="prior")
        if name=="logistic_balanced":
            return ml["Pipeline"]([
                ("scale",ml["StandardScaler"]()),
                ("model",ml["LogisticRegression"](
                    max_iter=250,
                    class_weight="balanced",
                    solver="lbfgs",
                    random_state=seed,
                )),
            ])
        if name=="hist_gradient_boosting":
            return ml["HistGradientBoostingClassifier"](
                learning_rate=0.08,
                max_iter=120,
                max_leaf_nodes=31,
                min_samples_leaf=30,
                l2_regularization=0.1,
                random_state=seed,
            )
        raise RuntimeError(f"UNKNOWN_CANDIDATE_{name}")

    @staticmethod
    def _fit(model,name,X,y,p):
        ml=MLModelTrainingValidationV2210._import_ml()
        if name=="hist_gradient_boosting":
            weights=ml["compute_sample_weight"](
                class_weight="balanced",y=y
            )
            model.fit(X,y,sample_weight=weights)
        else:
            model.fit(X,y)
        return model

    @staticmethod
    def _metrics(y_true,y_pred,labels):
        ml=MLModelTrainingValidationV2210._import_ml()
        accuracy=float(ml["accuracy_score"](y_true,y_pred))
        balanced=float(
            ml["balanced_accuracy_score"](y_true,y_pred)
        )
        macro=float(
            ml["f1_score"](
                y_true,y_pred,labels=labels,
                average="macro",zero_division=0
            )
        )
        weighted=float(
            ml["f1_score"](
                y_true,y_pred,labels=labels,
                average="weighted",zero_division=0
            )
        )
        cm=ml["confusion_matrix"](
            y_true,y_pred,labels=labels
        ).tolist()
        return {
            "accuracy":round(accuracy,8),
            "balanced_accuracy":round(balanced,8),
            "macro_f1":round(macro,8),
            "weighted_f1":round(weighted,8),
            "selection_score":round(
                (macro+balanced)/2.0,8
            ),
            "confusion_matrix_labels":list(labels),
            "confusion_matrix":cm,
            "rows":int(len(y_true)),
            "class_counts":dict(sorted(Counter(map(str,y_true)).items())),
        }

    def _walk_forward(self,name,X,y,dates,p):
        ml=self._import_ml()
        np=ml["np"]
        unique=sorted(set(map(str,dates)))
        folds=int(p["walk_forward_folds"])
        embargo=int(p["walk_forward_embargo_market_dates"])
        if folds<1 or len(unique)<8:
            return {
                "status":"INSUFFICIENT_DATES_FOR_WALK_FORWARD",
                "folds":[],
                "mean_selection_score":None,
            }

        # Use the later portion of TRAIN as sequential evaluation blocks.
        initial=max(3,int(len(unique)*0.55))
        remaining=len(unique)-initial-(folds*embargo)
        eval_size=max(1,remaining//folds)
        fold_reports=[]

        for k in range(folds):
            train_end=initial+k*(eval_size+embargo)
            embargo_start=train_end
            eval_start=embargo_start+embargo
            eval_end=(
                len(unique)
                if k==folds-1
                else min(len(unique),eval_start+eval_size)
            )
            train_dates=set(unique[:train_end])
            embargo_dates=unique[embargo_start:eval_start]
            eval_dates=set(unique[eval_start:eval_end])
            if not train_dates or not eval_dates:
                continue

            train_mask=np.asarray(
                [str(d) in train_dates for d in dates],
                dtype=bool
            )
            eval_mask=np.asarray(
                [str(d) in eval_dates for d in dates],
                dtype=bool
            )
            Xtr,ytr=X[train_mask],y[train_mask]
            Xev,yev=X[eval_mask],y[eval_mask]
            dummy_dates=np.asarray([""]*len(ytr),dtype=object)
            dummy_symbols=np.asarray([""]*len(ytr),dtype=object)
            Xtr,ytr,_,_,train_capped=self._cap_rows(
                Xtr,ytr,dummy_dates,dummy_symbols,
                int(p["max_walk_forward_train_rows"])
            )
            if len(yev)>int(p["max_walk_forward_eval_rows"]):
                idx=np.linspace(
                    0,len(yev)-1,
                    num=int(p["max_walk_forward_eval_rows"]),
                    dtype=int
                )
                Xev,yev=Xev[idx],yev[idx]
                eval_capped=True
            else:
                eval_capped=False

            model=self._candidate(name,p)
            self._fit(model,name,Xtr,ytr,p)
            pred=model.predict(Xev)
            metrics=self._metrics(
                yev,pred,p["class_labels"]
            )
            fold_reports.append({
                "fold":k+1,
                "train_date_start":min(train_dates),
                "train_date_end":max(train_dates),
                "embargo_dates":list(embargo_dates),
                "eval_date_start":min(eval_dates),
                "eval_date_end":max(eval_dates),
                "train_rows":int(len(ytr)),
                "eval_rows":int(len(yev)),
                "train_capped":bool(train_capped),
                "eval_capped":bool(eval_capped),
                "metrics":metrics,
            })

        scores=[
            f["metrics"]["selection_score"]
            for f in fold_reports
        ]
        return {
            "status":"PASS_BOUNDED_WALK_FORWARD"
                     if fold_reports
                     else "INSUFFICIENT_DATES_FOR_WALK_FORWARD",
            "folds":fold_reports,
            "mean_selection_score":(
                None if not scores
                else round(sum(scores)/len(scores),8)
            ),
        }

    def train_horizon(self,horizon):
        p=self.policy()
        ml=self._import_ml()
        paths=self._dataset_paths(horizon)

        # TEST IS DELIBERATELY NOT LOADED HERE.
        Xtr,ytr,dtr,str_symbols=self._read_csv(
            paths["train"],
            p["feature_columns"],
            p["target_column"],
        )
        Xva,yva,dva,sva=self._read_csv(
            paths["validation"],
            p["feature_columns"],
            p["target_column"],
        )
        train_original_rows=len(ytr)
        Xtr,ytr,dtr,str_symbols,train_capped=self._cap_rows(
            Xtr,ytr,dtr,str_symbols,
            int(p["max_train_rows_per_horizon"])
        )

        candidates={}
        fitted={}
        for name in p["candidate_models"]:
            model=self._candidate(name,p)
            self._fit(model,name,Xtr,ytr,p)
            pred=model.predict(Xva)
            metrics=self._metrics(
                yva,pred,p["class_labels"]
            )
            candidates[name]=metrics
            fitted[name]=model

        winner=max(
            candidates,
            key=lambda n:candidates[n]["selection_score"]
        )
        dummy_score=candidates["dummy_prior"]["selection_score"]
        winner_score=candidates[winner]["selection_score"]
        improvement=winner_score-dummy_score

        # Bounded walk-forward uses TRAIN only and selected model only.
        walk=self._walk_forward(
            winner,Xtr,ytr,dtr,p
        )

        # Only now, after selection is frozen, load untouched TEST.
        Xte,yte,dte,ste=self._read_csv(
            paths["test"],
            p["feature_columns"],
            p["target_column"],
        )
        selected=fitted[winner]
        test_pred=selected.predict(Xte)
        test_metrics=self._metrics(
            yte,test_pred,p["class_labels"]
        )

        edge_ready=(
            winner!="dummy_prior"
            and improvement>=float(
                p["minimum_validation_improvement_over_dummy"]
            )
        )

        model_path=self.models_dir/f"selected_{int(horizon)}m.joblib"
        ml["joblib"].dump(selected,model_path)

        report={
            "horizon_minutes":int(horizon),
            "generated_at_utc":_utcnow(),
            "feature_columns":list(p["feature_columns"]),
            "target_column":p["target_column"],
            "class_labels":list(p["class_labels"]),
            "train_source_rows":int(train_original_rows),
            "train_fit_rows":int(len(ytr)),
            "train_capped":bool(train_capped),
            "validation_rows":int(len(yva)),
            "test_rows":int(len(yte)),
            "candidate_validation_metrics":candidates,
            "selected_model":winner,
            "selected_validation_score":winner_score,
            "dummy_validation_score":dummy_score,
            "validation_improvement_over_dummy":
                round(improvement,8),
            "minimum_required_improvement":
                float(p["minimum_validation_improvement_over_dummy"]),
            "edge_ready":bool(edge_ready),
            "walk_forward":walk,
            "test_evaluated_after_selection":True,
            "test_used_for_selection":False,
            "test_metrics":test_metrics,
            "model_path":str(model_path.relative_to(self.root)),
            "model_sha256":_sha_file(model_path),
            "broker_network_used":False,
            "orders_submitted":0,
            "execution_selector_modified":False,
            "automatic_promotion":False,
            "live_trading":False,
        }
        report_path=self.reports_dir/f"horizon_{int(horizon)}m.json"
        _atomic_json(report_path,report)
        return report

    def train_all(self):
        pre=self.preflight()
        if pre["status"]!="PASS_ML_TRAINING_PREFLIGHT":
            _atomic_json(self.latest,pre)
            return pre
        if not pre["ml_dependencies_available"]:
            result={
                **pre,
                "status":"BLOCKED_ML_DEPENDENCIES_MISSING",
                "setup_command":
                    r"powershell -ExecutionPolicy Bypass -File .\START_V2_2_10_SETUP_ML_ENV.ps1",
            }
            _atomic_json(self.latest,result)
            return result

        p=self.policy()
        horizons={}
        for h in p["horizons_minutes"]:
            horizons[f"{int(h)}m"]=self.train_horizon(int(h))

        edge_horizons=[
            k for k,v in horizons.items()
            if v["edge_ready"]
        ]
        best_horizon=None
        if edge_horizons:
            best_horizon=max(
                edge_horizons,
                key=lambda k:
                    horizons[k]["test_metrics"]["selection_score"]
            )

        report={
            "stage":"AI_TRADING_ENGINE_V2_2_10_ML_MODEL_TRAINING_VALIDATION",
            "status":"PASS_ML_MODEL_TRAINING_VALIDATION",
            "generated_at_utc":_utcnow(),
            "source_dataset_manifest_sha256":
                _sha_file(self.dataset_manifest),
            "horizons":horizons,
            "edge_ready_horizons":edge_horizons,
            "best_test_horizon_for_shadow_research":best_horizon,
            "any_edge_ready":bool(edge_horizons),
            "test_set_used_for_selection":False,
            "test_evaluated_only_after_validation_selection":True,
            "bounded_walk_forward_enabled":True,
            "automatic_promotion":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.latest,report)
        return report

    def status(self):
        pre=self.preflight()
        if self.latest.exists():
            try:
                latest=json.loads(
                    self.latest.read_text(encoding="utf-8")
                )
                return latest
            except Exception:
                pass
        return pre
